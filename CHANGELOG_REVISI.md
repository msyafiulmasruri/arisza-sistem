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

## Perancangan ulang antarmuka (UI) sesuai Wireframe Revisi

- Tata letak utama diubah dari navigasi tab horizontal menjadi **Sidebar Navigasi tetap (`260px`)** di kiri dan **Topbar Header (`76px`)** dengan indikator akun `Pengelola` di kanan.
- **Halaman Login**: Kartu login terpusat dengan identitas `Arisza Library & Learning`, input email, input password, dan tombol `Login`.
- **Halaman Dashboard**:
  - Empat kartu ringkasan metrik di bagian atas (`Total Tanggapan`, `Positif`, `Netral`, `Negatif` beserta persentase).
  - Dua panel berdampingan di bagian tengah: grafik batang vertikal `Distribusi Sentimen` dan daftar `Hasil per Media Digital` dengan pintasan ke `Interpretasi`.
  - Panel `Word Cloud` tiga kolom (`Positif`, `Netral`, `Negatif`) sesuai media digital terpilih.
- **Halaman Impor Data**:
  - Dua panel berdampingan di bagian atas: `Unggah Dataset` (area dropzone seret berkas, tombol `Pilih File`, input opsional nama media, tombol `Unggah`) dan `Status File` (nama berkas, badge status, progress bar klasifikasi otomatis).
  - Tabel `Riwayat Unggah` di bagian bawah (`Nama File`, `Tanggal`, `Progres`, `Status` + tombol `Ulangi` bila gagal).
- **Halaman Data Tanggapan**:
  - Satu baris kontrol pencarian (`Cari tanggapan...`), filter media digital, filter sentimen, dan tombol `Unduh Hasil`.
  - Tabel 4 kolom (`No`, `Media Digital`, `Isi Tanggapan`, `Sentimen`) dengan navigasi halaman di bagian bawah.
- **Halaman Interpretasi**:
  - Bar kontrol pemilihan media digital, indikator status interpretasi, dan tombol `Jalankan Interpretasi`.
  - Panel `Pola Opini` terpisah menjadi 3 kolom sentimen berdampingan (`Positif`, `Netral`, `Negatif`) lengkap dengan tombol rincian `Kata & Frasa`.
  - Panel `Saran Tindak Lanjut` terpisah di bagian bawah dalam bentuk daftar poin bernomor (`1`, `2`, `3`).

## Pengujian

- Pengujian unit AI Service: 25 pengujian lulus pada lingkungan kerja ini.
- Pengujian mencakup konfigurasi tetap, pemuatan Hybrid tertunda, percobaan ulang setelah kegagalan pemuatan, frekuensi kata/frasa, interpretasi, dan kontrak database.
- Pemeriksaan sintaks Python dilakukan setelah perubahan.
- Koneksi langsung ke Neon, pengunduhan bobot model, pemuatan Llama di Hugging Face Spaces, dan pengujian deployment Vercel/Hugging Face tetap perlu dilakukan pada lingkungan production pengguna.
