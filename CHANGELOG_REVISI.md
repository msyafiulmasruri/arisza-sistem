# Catatan Revisi Sistem Arisza

## Interpretasi berbasis frekuensi dan pembaruan database

### Perubahan kode
- Python menghitung frekuensi kata dan frasa dua sampai tiga kata per media dan kategori sentimen.
- Maksimal 10 kata dan 10 frasa teratas dikirimkan kepada Llama 3.2 untuk menyusun pola opini.
- Llama menyusun saran tindak lanjut berdasarkan pola opini yang tersedia.
- Kata negasi dipertahankan saat penghitungan.
- Rincian kata, frasa, frekuensi, batas pengambilan, dan waktu penghitungan disimpan pada JSONB `interpretation_stages.detail`.
- Jalur pengujian langsung dan jalur pekerjaan sistem web menggunakan fungsi penghitungan yang sama.

### Perubahan database
- `interpretation_runs`: menggunakan `top_words`, `top_phrases`, `max_new_pola`, dan `max_new_saran`.
- `interpretation_stages`: tidak lagi menggunakan `chunks_total` dan `chunks_done`.
- Kolom lama `top_k`, `chunk_size`, `max_new_tokens`, `chunks_total`, dan `chunks_done` dihapus melalui `backend/migrasi_3.sql`.
- Tidak ada tabel yang dihapus atau dibuat baru untuk perubahan ini.
- Nilai konfigurasi keluaran untuk run lama dibiarkan NULL karena versi sebelumnya hanya menyimpan satu nilai gabungan, bukan batas pola dan saran secara terpisah.

### File SQL
- Database baru: jalankan `backend/schema.sql` di neon.

### Pengujian
- 8 pengujian unit frekuensi dan interpretasi menggunakan generator Llama tiruan.
- 4 pengujian statis skema dan migrasi database.
- Pemeriksaan sintaks Python berhasil.
- Pengujian langsung ke Neon, model Llama di Hugging Face Spaces, dan build frontend Vite belum dilakukan dalam lingkungan ini.
