# Sistem analisis sentimen Arisza

```
frontend/  React (Vite)                  -> Vercel (proyek 1)
backend/   FastAPI                       -> Vercel (proyek 2)
ai/        FastAPI + Hybrid + Llama      -> Hugging Face Space (Docker)
           PostgreSQL                    -> Neon
```

Alur: unggah CSV/Excel -> backend menyimpan baris ke PostgreSQL dan memanggil Space -> Space memprediksi sentimen
dan menulis hasilnya ke PostgreSQL. Tombol interpretasi membuat satu "run" per media. Space mengerjakan
positif, netral, negatif, lalu saran, dan menyimpan setiap tahap. Antarmuka hanya membaca status dari basis data.

## Urutan pemasangan

1. **Neon**: buat proyek, buka SQL Editor, jalankan `backend/schema.sql`, salin connection string (pooled).
2. **Space**: unggah ulang folder `ai/` (yang berubah: `app/db.py`, `app/tasks.py`, `app/main.py`, `app/config.py`,
   `requirements.txt`, `README.md`). Tambahkan secret `DATABASE_URL`. Ganti `API_KEY` dengan kunci baru.
3. **Backend**: proyek Vercel baru, Root Directory `backend`. Isi environment variables seperti `backend/.env.example`.
4. **Frontend**: proyek Vercel baru, Root Directory `frontend`, isi `VITE_API_URL` dengan alamat backend.
   Setelah itu isi `FRONTEND_ORIGIN` di backend dengan alamat frontend, lalu deploy ulang backend.

## Uji lokal

```
cd backend && pip install -r requirements.txt && uvicorn app:app --port 8000
cd frontend && cp .env.example .env && npm install && npm run dev
```

## Batas yang perlu diketahui

- Impor dan interpretasi berbagi satu antrean di Space (satu pekerja), jadi impor baru menunggu bila Llama sedang berjalan.
- Pekerjaan yang tidak bergerak 30 menit ditandai gagal otomatis (`BATAS_MACET_MENIT`) dan bisa diulang dari tahap yang gagal.
- Masuk memakai satu kata sandi bersama (`ADMIN_PASSWORD`). Belum ada akun per pengguna.
- Fungsi Vercel menerima isi permintaan sekitar 4,5 MB, jadi berkas impor dibatasi sekitar 4 MB.
