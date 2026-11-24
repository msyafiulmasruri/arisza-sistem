"""Konfigurasi tetap layanan AI Arisza.

Nilai model dan batas pemrosesan ditetapkan di kode agar konfigurasi
production Hugging Face Spaces hanya memuat secrets yang benar-benar rahasia.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "model"

# Secrets: atur melalui Hugging Face Spaces > Settings > Variables and secrets.
API_KEY = os.getenv("API_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Model interpretasi: konfigurasi tetap, tidak perlu dimasukkan ke ENV.
LLAMA_MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"
LLAMA_DTYPE = "bfloat16"
LLAMA_MAX_INPUT_TOKENS = 8192
LLAMA_MAX_NEW_POLA = 220
LLAMA_MAX_NEW_SARAN = 280

# Batas pemrosesan model utama dan penyimpanan status pekerjaan.
MAX_PREDICT_TEXTS = 200
PREDICT_BATCH_SIZE = 16
MAX_JOBS_KEPT = 50
