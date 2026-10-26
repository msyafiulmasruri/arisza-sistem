"""Model utama Hybrid IndoBERT-BiLSTM (hanya untuk prediksi, tanpa pelatihan)."""
import json
from pathlib import Path

from huggingface_hub import hf_hub_download  # <-- Tambahkan import ini
import torch
import torch.nn as nn
from transformers import AutoConfig, AutoModel, AutoTokenizer

from .preprocessing import preprocess


class HybridIndoBERTBiLSTM(nn.Module):
    """Susunan lapisan sama dengan notebook agar bobot tersimpan dapat dimuat."""

    def __init__(self, bert_config_path):
        super().__init__()
        config = AutoConfig.from_pretrained(bert_config_path)
        self.bert = AutoModel.from_config(config)
        self.bilstm = nn.LSTM(
            input_size=self.bert.config.hidden_size,
            hidden_size=128,
            num_layers=1,
            batch_first=True,
            bidirectional=True,
        )
        self.fc = nn.Linear(256, 128)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.4)
        self.classifier = nn.Linear(128, 3)

    def forward(self, input_ids, attention_mask):
        hidden = self.bert(
            input_ids=input_ids, attention_mask=attention_mask
        ).last_hidden_state
        lstm_output, _ = self.bilstm(hidden)
        mask = attention_mask.unsqueeze(-1).float()
        pooled = (lstm_output * mask).sum(dim=1)
        pooled = pooled / mask.sum(dim=1).clamp(min=1)
        x = self.relu(self.fc(pooled))
        return self.classifier(self.dropout(x))


class HybridService:

  def __init__(self, model_dir):
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    # 1. Pastikan file .pt diunduh otomatis dari Hugging Face Model Hub jika belum ada
    model_file_path = model_dir / "hybrid_indobert_bilstm.pt"
    if not model_file_path.exists():
      print(
          "File model lokal tidak ditemukan. Mengunduh dari Hugging Face Hub..."
      )
      downloaded_path = hf_hub_download(
          repo_id="rurisj/model-sentimen-hybridindobertbilstm",
          filename="hybrid_indobert_bilstm.pt",
      )
      # Pindahkan/salin file hasil unduhan ke folder model lokal aplikasi
      import shutil

      shutil.copy(downloaded_path, model_file_path)
      print("Model berhasil diunduh!")

    # 2. Baca file konfigurasi pendukung lainnya seperti biasa
    with open(model_dir / "model_info.json", encoding="utf-8") as f:
      self.info = json.load(f)
    with open(model_dir / "slang_map.json", encoding="utf-8") as f:
      self.slang_map = json.load(f)

    self.id2label = {int(k): v for k, v in self.info["id2label"].items()}
    self.max_length = int(self.info["max_length"])
    self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    self.tokenizer = AutoTokenizer.from_pretrained(model_dir / "tokenizer")
    self.model = HybridIndoBERTBiLSTM(
        bert_config_path=model_dir / "bert_config"
    )

    # 3. Load state dict dari file .pt lokal yang sudah diunduh
    state = torch.load(
        model_file_path, map_location="cpu", weights_only=True
    )
    self.model.load_state_dict(state)
    self.model.to(self.device).eval()

  def predict(self, texts, batch_size=16):
    """Kembalikan daftar hasil dengan urutan sama seperti masukan."""
    bersih = [preprocess(t, self.slang_map) for t in texts]
    hasil = [None] * len(texts)
    indeks = []
    for i, teks in enumerate(bersih):
      if teks:
        indeks.append(i)
      else:
        hasil[i] = {
            "text": texts[i],
            "clean_text": "",
            "status": "empty",
            "sentiment": None,
            "confidence": None,
            "probabilities": None,
        }

    for awal in range(0, len(indeks), batch_size):
      ids = indeks[awal : awal + batch_size]
      tokens = self.tokenizer(
          [bersih[i] for i in ids],
          padding="max_length",  # sama dengan pelatihan
          truncation=True,
          max_length=self.max_length,
          return_tensors="pt",
      )
      with torch.inference_mode():
        logits = self.model(
            tokens["input_ids"].to(self.device),
            tokens["attention_mask"].to(self.device),
        )
        probs = torch.softmax(logits, dim=1).cpu()
      for baris, i in enumerate(ids):
        p = probs[baris]
        label_id = int(torch.argmax(p).item())
        hasil[i] = {
            "text": texts[i],
            "clean_text": bersih[i],
            "status": "ok",
            "sentiment": self.id2label[label_id],
            "confidence": round(float(p[label_id]), 4),
            "probabilities": {
                self.id2label[j]: round(float(p[j]), 4) for j in range(3)
            },
        }
    return hasil