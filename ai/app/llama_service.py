"""Llama 3.2 3B Instruct resmi dari Meta (Hugging Face).

Model dimuat saat pertama kali dibutuhkan, bukan saat Space menyala,
agar jalur prediksi model utama tetap cepat.
"""
import copy
import threading
import time


class LlamaService:
    def __init__(self, model_id, hf_token="", dtype_name="bfloat16"):
        self.model_id = model_id
        self.hf_token = hf_token or None
        self.dtype_name = dtype_name
        self._lock = threading.Lock()
        self._model = None
        self._tokenizer = None
        self.load_seconds = None

    @property
    def loaded(self):
        return self._model is not None

    def ensure_loaded(self):
        with self._lock:
            if self._model is not None:
                return
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            dtype = {
                "bfloat16": torch.bfloat16,
                "float16": torch.float16,
                "float32": torch.float32,
            }[self.dtype_name]

            mulai = time.perf_counter()
            tokenizer = AutoTokenizer.from_pretrained(self.model_id, token=self.hf_token)
            try:
                model = AutoModelForCausalLM.from_pretrained(self.model_id, token=self.hf_token, dtype=dtype)
            except TypeError:  # versi transformers lama memakai nama torch_dtype
                model = AutoModelForCausalLM.from_pretrained(self.model_id, token=self.hf_token, torch_dtype=dtype)
            model.eval()
            self._tokenizer = tokenizer
            self._model = model
            self.load_seconds = round(time.perf_counter() - mulai, 2)

    def generate(self, messages, max_new_tokens):
        """Hasilkan teks secara deterministik (tanpa pengacakan)."""
        self.ensure_loaded()
        import torch

        inputs = self._tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, return_dict=True, return_tensors="pt"
        )
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        panjang_masukan = inputs["input_ids"].shape[1]

        config = copy.deepcopy(self._model.generation_config)
        config.do_sample = False
        config.temperature = None
        config.top_p = None
        config.top_k = None
        config.max_new_tokens = max_new_tokens
        if config.pad_token_id is None:
            eos = config.eos_token_id
            config.pad_token_id = eos[0] if isinstance(eos, (list, tuple)) else eos

        with torch.inference_mode():
            keluaran = self._model.generate(**inputs, generation_config=config)
        return self._tokenizer.decode(keluaran[0][panjang_masukan:], skip_special_tokens=True).strip()
