# Catatan Revisi Sistem Arisza

## Penyesuaian nama tabel dan relasi database

### Nama tabel baru
- `import_batches` diubah menjadi `batches`.
- `responses` tetap digunakan.
- `interpretation_runs` diubah menjadi `interpretations`.
- `interpretation_stages` diubah menjadi `interpretation_results`.
- `wordclouds` tetap digunakan.
- Kolom `run_id` pada `interpretation_results` diubah menjadi `interpretation_id`.

### Perubahan kode aplikasi
- Skema PostgreSQL pada `backend/schema.sql` diperbarui sesuai lima nama tabel baru.
- Query backend FastAPI dan AI Service disesuaikan dengan nama tabel serta kolom baru.
- Permintaan pekerjaan interpretasi ke AI Service kini menggunakan `interpretation_id`.
- Endpoint pengulangan interpretasi pada backend dan frontend diselaraskan menggunakan `/api/interpretations/{interpretation_id}/retry`.
- README utama dan README AI Service diperbarui sesuai struktur database terbaru.

### Migrasi database
- `backend/migrasi_penamaan_tabel.sql` disediakan untuk database lama.
- Migrasi mengganti nama tabel, kolom, sequence, dan indeks yang relevan tanpa menghapus data.
- Database baru cukup menggunakan `backend/schema.sql`.
- Database lama perlu di-backup, menghentikan sementara proses aplikasi, menjalankan migrasi penamaan, kemudian menjalankan skema terbaru.

### Pengujian yang dilakukan
- Pemeriksaan sintaks Python dengan `compileall` berhasil.
- 19 pengujian unit pada folder `test-ai/tests` berhasil dijalankan.
- Pengujian langsung ke database Neon, deployment Hugging Face Spaces/Vercel, dan build frontend Vite belum dilakukan dalam lingkungan ini.
