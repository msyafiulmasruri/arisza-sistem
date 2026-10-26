---
title: Arisza AI Service
emoji: 📚
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Arisza AI Service

Layanan AI untuk sistem analisis sentimen Arisza Library & Learning (FastAPI):

- `POST /predict`: preprocessing dan prediksi sentimen dengan Hybrid IndoBERT-BiLSTM.
- `POST /interpret`: interpretasi pola opini per media dengan Llama 3.2 3B Instruct (berjalan sebagai pekerjaan latar belakang).
- `GET /jobs/{job_id}`: status dan hasil pekerjaan interpretasi.
- `GET /health`: pemeriksaan layanan (tanpa kunci).

Semua endpoint selain `/health` memerlukan header `X-API-Key`.

## Secrets yang harus diisi (Settings > Variables and secrets)

| Nama | Isi |
|---|---|
| `API_KEY` | kunci rahasia buatanmu sendiri (teks acak yang panjang) |
| `HF_TOKEN` | token baca Hugging Face yang akunnya sudah menyetujui lisensi Llama 3.2 |

## Variables opsional

`LLAMA_TOP_K`, `LLAMA_MAX_NEW_TOKENS`, `LLAMA_DTYPE`, `MAX_TEXT_CHARS`, `MAX_PREDICT_TEXTS`, `PREDICT_BATCH_SIZE`.

Llama 3.2 is licensed under the Llama 3.2 Community License, Copyright © Meta Platforms, Inc. All Rights Reserved. Built with Llama.

## Endpoint untuk sistem web (membaca dan menulis ke PostgreSQL)

Tambahkan secret `DATABASE_URL` (URL koneksi Neon).

- `POST /jobs/classify` dengan `{"batch_id": 1}`: memprediksi sentimen semua baris `pending` pada batch impor.
- `POST /jobs/interpret` dengan `{"run_id": 1}`: menjalankan interpretasi bertahap (positif, netral, negatif, saran) dan menyimpan tiap tahap.

Kedua pekerjaan berbagi satu antrean (satu pekerja), jadi impor baru menunggu bila interpretasi sedang berjalan.
