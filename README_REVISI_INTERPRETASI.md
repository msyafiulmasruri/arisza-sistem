# Revisi Sistem Interpretasi Llama 3.2 — Arisza Library & Learning

Paket ini menyelaraskan AI Service, backend, frontend, dan skema database dengan metode interpretasi terbaru: Llama 3.2 menerima teks tanggapan asli yang dikelompokkan menurut media digital dan kategori sentimen.

## Ringkasan perubahan

### 1. AI Service (`test-ai/`)
- Sumber interpretasi berubah dari `clean_text` dan daftar frekuensi kata/frasa menjadi teks asli pada `responses.text`.
- Teks dikelompokkan menjadi sentimen positif, netral, dan negatif untuk setiap media digital.
- Prompt terstruktur menyertakan teks tanggapan sebagai data, bukan instruksi.
- Token masukan dihitung dengan tokenizer dan chat template Llama.
- Batas masukan aplikasi ditetapkan 8.192 token per pemanggilan. Jika satu kelompok melebihi batas, teks dibagi menjadi beberapa batch, setiap batch diringkas, lalu ringkasan digabungkan menjadi satu pola opini akhir.
- Setelah pola opini kategori tersedia, Llama menyusun tiga saran tindak lanjut.
- Metode baru diberi identitas `teks_asli_batch_v2`.

### 2. Frontend (`frontend/`)
- Bagian tampilan "Kata & Frasa" dihapus.
- Halaman interpretasi tetap menampilkan pola opini positif, netral, dan negatif serta tiga saran tindak lanjut.
- Status proses, pesan kesalahan, dan catatan hasil tetap ditampilkan.

### 3. Backend dan database (`backend/`)
- Backend mengenali hasil baru `teks_asli_batch_v2`.
- Hasil lama `frekuensi_v1` akan ditandai perlu diperbarui, bukan dihapus.
- Kolom `max_input_tokens` ditambahkan pada tabel `interpretations`.
- Kolom lama `top_words` dan `top_phrases` tidak dihapus agar kompatibel dengan database yang sudah digunakan; aplikasi versi baru tidak lagi memakainya.

## Urutan penerapan

1. **Cadangkan database Neon terlebih dahulu.** Jangan melewati langkah ini.
2. Jalankan `backend/migrasi_interpretasi_teks_asli.sql` satu kali pada database yang sudah ada. Migrasi ini hanya menambahkan kolom `max_input_tokens`; tidak menghapus data atau kolom lama.
3. Deploy isi folder `test-ai/` ke Hugging Face Space AI Service. Pertahankan Secrets yang sudah digunakan (`API_KEY`, `DATABASE_URL`, dan `HF_TOKEN`).
4. Deploy isi folder `backend/` ke project backend Vercel. Pertahankan environment variables yang sudah digunakan (`DATABASE_URL`, `SESSION_SECRET`, `SPACE_URL`, `SPACE_API_KEY`, serta token Space privat jika diperlukan).
5. Deploy isi folder `frontend/` ke project frontend. Pertahankan konfigurasi `VITE_API_URL` sesuai alamat backend.
6. Setelah seluruh layanan aktif, buka sistem dan jalankan ulang interpretasi untuk setiap media digital. Hasil lama akan ditandai "Perlu diperbarui" karena masih menggunakan metode frekuensi kata/frasa.

Untuk database baru, gunakan `backend/schema.sql`; migrasi tambahan tidak diperlukan jika kolom `max_input_tokens` sudah dibuat dari skema tersebut.

## Konfigurasi batas masukan

`test-ai/app/config.py` menetapkan `LLAMA_MAX_INPUT_TOKENS = 8192`. Nilai ini merupakan batas operasional aplikasi per pemanggilan Llama, bukan klaim bahwa batas konteks asli model hanya 8.192 token. Nilainya dapat disesuaikan setelah pengujian sumber daya Hugging Face Space. Panjang keluaran tetap 220 token untuk pola opini dan 280 token untuk saran tindak lanjut.

## Pengujian yang dilakukan

- 23 pengujian Python AI Service lulus, termasuk pengujian penggunaan teks asli, pembagian batch, penggabungan ringkasan, dan penyusunan tiga saran.
- Seluruh file Python AI Service dan backend lolos pemeriksaan sintaks (`py_compile`).
- File JSX `frontend/src/Interpretasi.jsx` lolos pemeriksaan sintaks JSX.
- Build frontend penuh belum dijalankan karena dependensi npm tidak tersedia di cache lingkungan pemeriksaan.
- Pengujian backend penuh belum dijalankan karena paket `psycopg` tidak tersedia di lingkungan pemeriksaan.

## Keamanan berkas

Berkas `.env` lokal tidak disertakan dalam ZIP untuk melindungi kredensial. Gunakan `.env.example` sebagai contoh dan isi kredensial sendiri di lingkungan deployment. Jangan mengunggah `.env` ke repositori publik.
