# Catatan Revisi Sistem Arisza

## Revisi konfigurasi AI Service dan koneksi production

- Parameter model dan batas pemrosesan dipindahkan dari Environment Variables ke `test-ai/app/config.py` sebagai konfigurasi tetap: model Llama 3.2 3B Instruct, dtype bfloat16, 10 kata, 10 frasa, 220 token pola opini, 280 token saran, maksimal 200 teks per permintaan, batch 16, dan 50 riwayat pekerjaan.
- `test-ai/.env.example` kini hanya memuat tiga secrets yang diperlukan: `API_KEY`, `DATABASE_URL`, dan `HF_TOKEN`.
- Pengunduhan bobot Hybrid menggunakan `HF_TOKEN` bila repository Model Hub bersifat private.
- Bobot Hybrid IndoBERT-BiLSTM tidak lagi diunduh/dimuat pada saat startup FastAPI. Model dimuat saat klasifikasi pertama diminta melalui `LazyHybridService`.
- Kegagalan pemuatan Hybrid dicatat di log dan dapat dicoba kembali pada permintaan berikutnya. Endpoint `/health` tetap dapat merespons selama proses pemuatan model belum berhasil.
- Endpoint `/health` menampilkan status pemuatan Hybrid (`not_loaded`, `loaded`, atau `load_failed`) dan status pemuatan Llama.
- Backend melakukan percobaan ulang singkat untuk koneksi sementara ke Hugging Face Space dan memberikan pesan diagnostik yang lebih jelas untuk kegagalan koneksi atau respons HTTP.
- README utama dan README AI Service diperbarui agar sesuai dengan arsitektur production: frontend dan backend di Vercel, AI Service di Hugging Face Spaces, model Hybrid dan Llama diunduh dari Model Hub, serta PostgreSQL di Neon.

## Autentikasi akun email dan kata sandi

- Login frontend meminta email dan kata sandi.
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

## Pengujian

- Pengujian unit AI Service: 25 pengujian lulus pada lingkungan kerja ini.
- Pengujian mencakup konfigurasi tetap, pemuatan Hybrid tertunda, percobaan ulang setelah kegagalan pemuatan, frekuensi kata/frasa, interpretasi, dan kontrak database.
- Pemeriksaan sintaks Python dilakukan setelah perubahan.
- Koneksi langsung ke Neon, pengunduhan bobot model, pemuatan Llama di Hugging Face Spaces, dan pengujian deployment Vercel/Hugging Face tetap perlu dilakukan pada lingkungan production pengguna.
