# Sistem Analisis Sentimen Arisza Library & Learning

## Komponen sistem

```text
frontend/  React + Vite                 -> Vercel (proyek frontend)
backend/   FastAPI                      -> Vercel (proyek backend)
test-ai/   FastAPI + Hybrid + Llama     -> Hugging Face Spaces (Docker)
PostgreSQL                               -> Neon
```

Frontend berkomunikasi dengan backend. Backend mengelola data dan mengirim permintaan pemrosesan ke layanan AI. Layanan AI menjalankan klasifikasi Hybrid IndoBERT-BiLSTM, membuat Word Cloud, dan menjalankan interpretasi Llama 3.2. Backend dan layanan AI membaca atau menyimpan hasil ke PostgreSQL sesuai kebutuhan proses.

## Struktur database

Database menggunakan lima tabel utama:

- `batches`: informasi proses impor data.
- `responses`: data tanggapan, hasil klasifikasi, dan teks hasil preprocessing.
- `interpretations`: informasi dan status proses interpretasi per media.
- `interpretation_results`: hasil interpretasi setiap kategori sentimen dan saran tindak lanjut.
- `wordclouds`: gambar Word Cloud berdasarkan media dan kategori sentimen.

Relasi utama:

- `batches` ke `responses`: satu proses impor dapat memiliki banyak tanggapan (`1:N`).
- `interpretations` ke `interpretation_results`: satu proses interpretasi memiliki beberapa hasil tahap (`1:N`).
- `wordclouds` menggunakan gabungan `media` dan `label` sebagai primary key dan tidak memiliki foreign key langsung.

## Urutan pemasangan dan pembaruan

### Database baru

1. Buat database PostgreSQL di Neon.
2. Jalankan `backend/schema.sql` melalui SQL Editor Neon.

### Database lama yang masih menggunakan nama tabel sebelumnya

1. Hentikan sementara backend dan layanan AI, serta pastikan tidak ada proses impor atau interpretasi yang sedang berjalan.
2. Buat backup database.
3. Jalankan `backend/migrasi_penamaan_tabel.sql` satu kali. Migrasi ini mengganti nama tabel dan kolom yang diperlukan tanpa menghapus data.
4. Jalankan `backend/schema.sql` untuk memastikan skema dan indeks tersedia.
5. Deploy ulang layanan AI, backend, dan frontend dengan kode terbaru.

Jangan menjalankan migrasi penamaan pada database baru yang sudah menggunakan nama tabel baru. Jika database berisi nama tabel lama dan baru secara bersamaan, hentikan proses dan periksa database terlebih dahulu; skrip migrasi sengaja menghentikan proses agar tidak menimpa atau menggabungkan data secara keliru.

## Konfigurasi layanan

1. **Hugging Face Spaces**: folder `test-ai/` merupakan layanan AI terpisah. Isi secret `API_KEY`, `HF_TOKEN`, dan `DATABASE_URL` pada pengaturan Space.
2. **Backend Vercel**: gunakan folder `backend/` sebagai Root Directory. Isi variabel lingkungan berdasarkan `backend/.env.example`.
3. **Frontend Vercel**: gunakan folder `frontend/` sebagai Root Directory. Isi `VITE_API_URL` dengan alamat backend. Atur `FRONTEND_ORIGIN` pada backend sesuai alamat frontend.

## Pengujian lokal

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --port 8000
```

Frontend:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Layanan AI:

```bash
cd test-ai
python -m unittest discover -s tests -v
```

## Catatan operasional

- Prediksi sentimen dan interpretasi Llama menggunakan antrean pekerjaan yang terpisah pada layanan AI.
- Proses klasifikasi menghasilkan label positif, netral, atau negatif, beserta nilai confidence.
- Interpretasi dilakukan per media digital. Python menghitung frekuensi kata dan frasa, kemudian Llama menyusun pola opini dan saran tindak lanjut.
- Pekerjaan yang tidak bergerak melewati batas waktu akan ditandai gagal oleh backend dan dapat diulang melalui sistem.
- Akses sistem masih menggunakan satu kata sandi bersama (`ADMIN_PASSWORD`), belum menggunakan akun individual.
- Berkas impor dibatasi maksimal 5.000 baris dan ukuran sekitar 4 MB sesuai konfigurasi backend.
