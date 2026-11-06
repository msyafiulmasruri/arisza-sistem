# Catatan Revisi Sistem Arisza

## Autentikasi akun email dan kata sandi

- Login frontend kini meminta email dan kata sandi.
- Backend memverifikasi akun pada tabel `users`.
- Password disimpan dalam bentuk PBKDF2-HMAC-SHA256 hash melalui skrip `backend/create_user.py`.
- Backend menerbitkan token akses bertanda tangan HMAC; frontend menyimpannya sementara di `sessionStorage` dan mengirimkannya melalui `Authorization: Bearer`.
- `ADMIN_PASSWORD` dan header `X-Admin-Key` dihapus dari mekanisme autentikasi.
- `SESSION_SECRET` menjadi secret backend untuk menandatangani token, bukan password login.
- Token berlaku 12 jam secara default; logout menghapus token dari sesi browser.

## Penyesuaian database

- Ditambahkan tabel `users` dengan kolom `id`, `email`, `password_hash`, dan `created_at`.
- Ditambahkan `user_id` pada tabel `batches` dan `interpretations`.
- Relasi yang diterapkan: `users` 1:N `batches`; `users` 1:N `interpretations`; `batches` 1:N `responses`; `interpretations` 1:N `interpretation_results`.
- `wordclouds` tetap menggunakan primary key gabungan `media` dan `label` tanpa foreign key langsung.
- Seluruh akun terdaftar menggunakan ruang data analisis bersama. `user_id` mencatat akun yang membuat proses impor dan interpretasi; belum ada pemisahan data per akun atau pembagian hak akses berbasis peran.

## Migrasi database

- `backend/schema.sql` digunakan untuk database baru.
- `backend/migrasi_penamaan_tabel.sql` digunakan pada database lama untuk mengganti nama tabel, membuat tabel `users`, dan menambahkan kolom `user_id` sementara dalam kondisi nullable.
- `backend/create_user.py` membuat akun, mengaitkan data lama yang belum memiliki `user_id` dengan akun pertama, lalu menetapkan `user_id` menjadi `NOT NULL`.
- Backup database wajib dibuat sebelum migrasi.

## Pengujian yang dilakukan

- Pengujian unit untuk hashing password dan validasi token akses.
- Pemeriksaan sintaks Python.
- Pengujian unit AI Service.
- Pemeriksaan statis kontrak schema, migrasi, backend, dan frontend.
- Smoke test API autentikasi dengan database tiruan: login salah ditolak, login benar menghasilkan token, dan token dapat digunakan untuk endpoint pengguna aktif.
- Build frontend Vite belum dijalankan karena dependensi npm tidak tersedia di lingkungan kerja ini. Pengujian langsung ke Neon dan deployment Vercel/Hugging Face tetap perlu dilakukan pada lingkungan deployment pengguna.

## Persiapan development lokal

- Menambahkan `uvicorn[standard]` dan `python-dotenv` ke dependensi backend agar FastAPI dapat dijalankan lokal dan membaca `.env` melalui `--env-file`.
- Menambahkan pemuatan `backend/.env` pada `create_user.py`, sehingga akun dapat dibuat dari terminal tanpa menempelkan `DATABASE_URL` secara manual.
- Menambahkan `python-dotenv` dan `uvicorn[standard]` ke dependensi AI Service serta panduan pemasangan PyTorch CPU terpisah.
- Menambahkan `test-ai/.env.example` untuk konfigurasi API key, Neon, dan token Hugging Face.
- Menyesuaikan `backend/.env.example` agar mengarah ke AI Service lokal pada `127.0.0.1:7860`.
- Menambahkan dan memperluas `.gitignore` untuk mengecualikan `.venv`, `venv`, `node_modules`, `.env`, cache Python, hasil build, bobot model, dan file sementara. File `.env.example` tetap dapat di-commit.
- Memperbarui `.dockerignore` agar rahasia dan artefak development lokal tidak ikut masuk ke image AI Service.
- Memperbarui README utama dan README AI Service dengan panduan setup lokal untuk frontend, backend, dan AI Service, termasuk opsi tetap menggunakan Hugging Face Spaces.
