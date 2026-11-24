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

Layanan FastAPI untuk preprocessing, klasifikasi sentimen Hybrid IndoBERT-BiLSTM, pembuatan Word Cloud, dan interpretasi menggunakan Llama 3.2 3B Instruct. Layanan ini dijalankan pada Hugging Face Spaces dan diakses oleh backend Arisza melalui HTTP API.

## Secrets Hugging Face Spaces

Buka **Settings → Variables and secrets** pada Space, lalu tambahkan tiga Secrets berikut:

| Nama | Fungsi |
|---|---|
| `API_KEY` | Kunci pada header `X-API-Key`; harus sama dengan `SPACE_API_KEY` di backend Vercel. |
| `DATABASE_URL` | URL PostgreSQL Neon yang sama dengan backend. |
| `HF_TOKEN` | Token Hugging Face yang memiliki akses ke model Llama 3.2 dan repository bobot Hybrid jika repository tersebut private. |

Konfigurasi model dan batas pemrosesan sudah ditetapkan langsung di `app/config.py`, sehingga tidak perlu dibuat sebagai Variables/Secrets tambahan. Nilainya adalah model `meta-llama/Llama-3.2-3B-Instruct`, `bfloat16`, batas masukan 8.192 token untuk setiap pemanggilan Llama, maksimal 220 token untuk pola opini, maksimal 280 token untuk saran tindak lanjut, maksimal 200 teks per permintaan prediksi, batch prediksi 16, dan maksimal 50 riwayat pekerjaan.

## Model yang digunakan

- **Hybrid IndoBERT-BiLSTM:** bobot diunduh dari repository Model Hub `rurisj/model-sentimen-hybridindobertbilstm` ketika klasifikasi pertama kali diminta. Token `HF_TOKEN` digunakan jika repository bersifat private. Berkas konfigurasi, tokenizer, dan pemetaan slang tersedia di folder `model/`.
- **Llama 3.2 3B Instruct:** diunduh dari `meta-llama/Llama-3.2-3B-Instruct` ketika interpretasi pertama kali diminta. `HF_TOKEN` digunakan untuk mengakses model; token bukan API key dari Meta.


## Metode interpretasi tanggapan

Interpretasi menggunakan teks tanggapan asli dari kolom `responses.text`, bukan daftar frekuensi kata/frasa dan bukan `clean_text`. Teks dikelompokkan berdasarkan media digital dan label sentimen positif, netral, atau negatif. Setiap kelompok dikirim ke Llama melalui prompt terstruktur.

Batas masukan aplikasi ditetapkan sebesar 8.192 token untuk setiap pemanggilan Llama. Jumlah token dihitung menggunakan tokenizer Llama dan chat template yang sama dengan proses generasi. Jika seluruh teks dalam satu kelompok melebihi batas tersebut, teks dibagi menjadi beberapa batch. Setiap batch diringkas oleh Llama, kemudian ringkasan batch digabungkan menjadi satu pola opini akhir untuk kategori sentimen tersebut. Jika teks muat dalam satu masukan, Llama langsung menyusun pola opini akhir.

Setelah pola opini dari kategori yang memiliki tanggapan tersedia, Llama menyusun tepat tiga saran tindak lanjut berdasarkan keseluruhan pola opini. Isi tanggapan diperlakukan sebagai data, bukan instruksi, dan model diarahkan agar tidak menambahkan informasi yang tidak didukung oleh tanggapan.

Metode baru disimpan dengan identitas `teks_asli_batch_v2`. Hasil interpretasi lama yang menggunakan `frekuensi_v1` tidak dihapus, tetapi ditandai perlu diperbarui oleh backend agar dapat dibuat ulang menggunakan metode baru.

## Startup dan pemeriksaan layanan

FastAPI dijalankan pada `0.0.0.0:7860` sesuai konfigurasi Docker Space. Server tidak lagi memuat bobot Hybrid saat startup. Bobot Hybrid dimuat saat pekerjaan klasifikasi pertama diminta, sedangkan Llama dimuat saat interpretasi pertama diminta. Dengan demikian, proses unduh atau pemuatan model tidak menghalangi endpoint kesehatan untuk merespons.

Setelah Space selesai membangun dan berjalan, buka:

- `https://NAMA-SPACE.hf.space/health`
- `https://NAMA-SPACE.hf.space/docs`

Endpoint `/health` harus mengembalikan JSON dengan `status: ok`. `hybrid_status: not_loaded` sebelum klasifikasi pertama adalah kondisi normal. Setelah klasifikasi pertama berhasil, nilainya menjadi `loaded`.

## Pengaturan backend Vercel

Pada project backend Vercel, pastikan:

- `SPACE_URL` berisi alamat Space, misalnya `https://NAMA-SPACE.hf.space` (bukan URL halaman `huggingface.co/spaces/...` dan tanpa path `/health`).
- `SPACE_API_KEY` sama persis dengan Secret `API_KEY` pada Space.
- `HF_SPACE_TOKEN` hanya diisi jika Space bersifat private.

Jika backend menampilkan `Connection refused`, periksa apakah `/health` dapat dibuka langsung, lalu periksa Logs dan Container logs pada Space. Pastikan build berhasil, Docker menjalankan Uvicorn pada `0.0.0.0:7860`, dan `app_port` tetap `7860`.

## Menjalankan secara lokal (opsional)

Dari folder `test-ai`:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
Copy-Item .env.example .env
```

Isi `API_KEY`, `DATABASE_URL`, dan `HF_TOKEN` di `.env`, kemudian jalankan:

```powershell
uvicorn app.main:app --reload --env-file .env --host 127.0.0.1 --port 7860
```

Penggunaan lokal membutuhkan sumber daya memori yang cukup untuk model Llama 3.2 3B. Untuk deployment production, model tetap dijalankan di Hugging Face Spaces.

## Endpoint

- `GET /health`: status layanan dan status pemuatan model.
- `POST /predict`: prediksi sentimen langsung.
- `POST /interpret`: interpretasi langsung untuk pengujian.
- `GET /jobs/{job_id}`: status pekerjaan interpretasi langsung.
- `POST /jobs/classify`: klasifikasi batch dari database.
- `POST /jobs/interpret`: interpretasi berdasarkan ID proses pada database.
- `POST /jobs/complete`: melengkapi teks preprocessing data lama.
- `POST /jobs/wordcloud`: membuat ulang Word Cloud.

Semua endpoint selain `/health` memerlukan header `X-API-Key`.

## Pengujian

Dari folder `test-ai`, jalankan pengujian layanan AI:

```powershell
python -m unittest discover -s tests -p "test_config_startup.py" -v
python -m unittest discover -s tests -p "test_interpret.py" -v
```

Pemeriksaan integrasi yang membaca folder `frontend` dan `backend` dijalankan dari folder utama paket gabungan:

```powershell
$env:PYTHONPATH = "test-ai"
python -m unittest discover -s test-ai/tests -v
```

## Database

AI Service membaca dan menulis tabel `batches`, `responses`, `interpretations`, `interpretation_results`, dan `wordclouds` pada database Neon. Struktur tabel dibuat melalui `backend/schema.sql`; migrasi database lama dilakukan melalui `backend/migrasi_penamaan_tabel.sql`.
