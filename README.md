# Sistem Analisis Sentimen Arisza Library & Learning

## Komponen sistem

```text
frontend/  React + Vite                 -> Vercel (proyek frontend)
backend/   FastAPI                      -> Vercel (proyek backend)
test-ai/   FastAPI + Hybrid + Llama     -> Hugging Face Spaces (Docker)
PostgreSQL                               -> Neon
```

Frontend berkomunikasi dengan backend. Backend mengelola autentikasi dan data, kemudian mengirim permintaan pemrosesan ke layanan AI. Layanan AI menjalankan klasifikasi Hybrid IndoBERT-BiLSTM, membuat Word Cloud, dan menjalankan interpretasi Llama 3.2. Backend dan layanan AI membaca atau menyimpan hasil ke PostgreSQL sesuai kebutuhan proses.

## Struktur database

Database menggunakan enam tabel utama:

- `users`: akun login yang menyimpan email dan password hash.
- `batches`: informasi proses impor dan akun yang mengunggah data.
- `responses`: data tanggapan, hasil klasifikasi, dan teks hasil preprocessing.
- `interpretations`: informasi proses interpretasi dan akun yang menjalankannya.
- `interpretation_results`: hasil interpretasi setiap kategori sentimen dan saran tindak lanjut.
- `wordclouds`: gambar Word Cloud berdasarkan media dan kategori sentimen.

Relasi utama:

- `users` ke `batches`: satu pengguna dapat membuat beberapa proses impor (`1:N`).
- `users` ke `interpretations`: satu pengguna dapat menjalankan beberapa proses interpretasi (`1:N`).
- `batches` ke `responses`: satu proses impor dapat memiliki banyak tanggapan (`1:N`).
- `interpretations` ke `interpretation_results`: satu proses interpretasi memiliki beberapa hasil tahap (`1:N`).
- `wordclouds` menggunakan gabungan `media` dan `label` sebagai primary key dan tidak memiliki foreign key langsung.

**Ruang kerja data:** seluruh akun yang terdaftar menggunakan ruang data analisis yang sama. Kolom `user_id` mencatat akun yang membuat proses impor dan interpretasi, bukan memisahkan data tanggapan per akun. Sistem belum menerapkan pembagian hak akses berdasarkan peran.

## Urutan pemasangan dan pembaruan

### Database baru

1. Buat database PostgreSQL di Neon.
2. Jalankan `backend/schema.sql` melalui SQL Editor Neon.
3. Buat akun pertama menggunakan `backend/create_user.py` (petunjuk di bawah).

### Database lama yang masih menggunakan nama tabel sebelumnya

1. Hentikan sementara backend dan layanan AI, serta pastikan tidak ada proses impor atau interpretasi yang sedang berjalan.
2. Buat backup database.
3. Jalankan `backend/migrasi_penamaan_tabel.sql` satu kali. Migrasi ini mengganti nama tabel dan kolom yang diperlukan, membuat tabel `users`, serta menambahkan `user_id` sementara dalam kondisi nullable agar data lama dapat dipertahankan.
4. Jalankan `backend/schema.sql` untuk memastikan tabel dan indeks tersedia.
5. Jalankan `backend/create_user.py`. Akun pertama yang dibuat akan dikaitkan dengan data impor dan interpretasi lama yang belum memiliki `user_id`. Skrip kemudian menetapkan kolom tersebut menjadi `NOT NULL`.
6. Deploy ulang layanan AI, backend, dan frontend dengan kode terbaru.

Jangan menjalankan migrasi penamaan pada database baru yang sudah menggunakan nama tabel baru. Jika database berisi nama tabel lama dan baru secara bersamaan, hentikan proses dan periksa database terlebih dahulu; skrip migrasi sengaja menghentikan proses agar tidak menimpa atau menggabungkan data secara keliru.

### Membuat akun pengguna

Akun tidak dibuat melalui halaman pendaftaran pada frontend. Akun dibuat oleh pengelola melalui skrip backend agar akses akun dapat dikendalikan.

1. Pastikan `DATABASE_URL` sudah diarahkan ke database Neon yang benar.
2. Masuk ke folder `backend/`, pasang dependensi, lalu jalankan:

```bash
pip install -r requirements.txt
python create_user.py --email pengelola@arisza.id
```

3. Masukkan kata sandi dua kali ketika diminta. Kata sandi minimal 12 karakter dan disimpan sebagai hash PBKDF2-HMAC-SHA256, bukan teks biasa.
4. Jalankan skrip yang sama dengan email berbeda untuk menambahkan akun lain.

Contoh PowerShell untuk mengatur `DATABASE_URL` sebelum menjalankan skrip:

```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST/neondb?sslmode=require"
python create_user.py --email pengelola@arisza.id
```

## Konfigurasi layanan

1. **Hugging Face Spaces**: folder `test-ai/` merupakan layanan AI terpisah. Isi secret `API_KEY`, `HF_TOKEN`, dan `DATABASE_URL` pada pengaturan Space.
2. **Backend Vercel**: gunakan folder `backend/` sebagai Root Directory. Isi variabel lingkungan berdasarkan `backend/.env.example`. Buat `SESSION_SECRET` acak minimal 32 karakter, misalnya dengan perintah `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Jangan gunakan `ADMIN_PASSWORD` lagi.
3. **Frontend Vercel**: gunakan folder `frontend/` sebagai Root Directory. Isi `VITE_API_URL` dengan alamat backend. Atur `FRONTEND_ORIGIN` pada backend sesuai alamat frontend.

## Mekanisme autentikasi

- Pengguna login menggunakan email dan kata sandi yang terdaftar pada tabel `users`.
- Backend memverifikasi password hash dan mengeluarkan token akses bertanda tangan.
- Frontend menyimpan token sementara di `sessionStorage` dan mengirimkannya melalui header `Authorization: Bearer` untuk permintaan yang memerlukan autentikasi.
- Token berlaku selama 12 jam secara default. Logout menghapus token dari sesi browser.
- `SESSION_SECRET` digunakan untuk menandatangani dan memverifikasi token; variabel ini bukan kata sandi akun pengguna.
- Akun dibuat melalui skrip `create_user.py`, bukan melalui halaman pendaftaran.

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
- Berkas impor dibatasi maksimal 5.000 baris dan ukuran sekitar 4 MB sesuai konfigurasi backend.
- Data analisis digunakan bersama oleh akun-akun yang terdaftar; `user_id` pada proses impor dan interpretasi berfungsi sebagai pencatat akun pelaksana.

### Konsistensi relasi database

Kolom `responses.batch_id` wajib terisi (`NOT NULL`) agar setiap tanggapan terhubung ke satu proses impor. Pada database lama, migrasi memeriksa apakah masih terdapat baris dengan `batch_id` kosong. Jika ditemukan, migrasi dihentikan dan data perlu diperiksa terlebih dahulu; skrip tidak menghapus atau mengisi relasi secara otomatis.
