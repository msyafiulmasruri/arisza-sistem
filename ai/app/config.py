"""Pengaturan layanan AI.

Semua nilai bisa diubah lewat Settings > Variables and secrets pada Space,
tanpa mengubah kode. Nilai bawaan di bawah hanya titik awal untuk uji coba.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.getenv("MODEL_DIR", str(BASE_DIR / "model")))

# Rahasia: isi lewat "Secrets" pada Space, jangan ditulis di kode.
API_KEY = os.getenv("API_KEY", "")      # kunci yang harus dikirim backend pada header X-API-Key
HF_TOKEN = os.getenv("HF_TOKEN", "")    # token Hugging Face yang sudah disetujui untuk model Llama
DATABASE_URL = os.getenv("DATABASE_URL", "")  # URL PostgreSQL Neon (sebaiknya akun dengan hak terbatas)

# Llama 3.2 3B Instruct resmi dari Meta.
LLAMA_MODEL_ID = os.getenv("LLAMA_MODEL_ID", "meta-llama/Llama-3.2-3B-Instruct")
LLAMA_DTYPE = os.getenv("LLAMA_DTYPE", "bfloat16")          # bfloat16 | float16 | float32
LLAMA_TOP_K = int(os.getenv("LLAMA_TOP_K", "15"))           # jumlah teks per sentimen (TENTUKAN LEWAT UJI COBA)
LLAMA_MAX_NEW_TOKENS = int(os.getenv("LLAMA_MAX_NEW_TOKENS", "300"))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "300"))    # panjang maksimal tiap teks yang dikirim ke Llama

# Model utama.
PREDICT_BATCH_SIZE = int(os.getenv("PREDICT_BATCH_SIZE", "16"))
MAX_PREDICT_TEXTS = int(os.getenv("MAX_PREDICT_TEXTS", "200"))  # batas teks per permintaan /predict

MAX_JOBS_KEPT = int(os.getenv("MAX_JOBS_KEPT", "50"))
