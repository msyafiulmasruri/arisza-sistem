# Sistem analisis sentimen Arisza

```
frontend/  React (Vite)                  -> Vercel (proyek 1)
backend/   FastAPI                       -> Vercel (proyek 2)
test-ai/   FastAPI + Hybrid + Llama      -> Hugging Face Space (Docker)
           PostgreSQL                    -> Neon
```

Alur: unggah CSV/Excel -> backend menyimpan baris ke PostgreSQL dan memanggil Space -> Space memprediksi sentimen
dan menulis hasilnya ke PostgreSQL. Tombol interpretasi membuat satu "run" per media. Python menghitung
frekuensi kata dan frasa pada setiap sentimen; Llama menyusun pola opini positif, netral, negatif, lalu saran.
Rincian frekuensi dan hasil setiap tahap disimpan di PostgreSQL. Antarmuka membaca status dari basis data.

## Urutan pemasangan

1. **Neon**: untuk database baru, jalankan `backend/schema.sql`. Untuk database yang sudah dipakai versi sebelumnya, lakukan pembaruan terjadwal: pastikan tidak ada interpretasi yang sedang berjalan, jalankan `backend/migrasi_3.sql`, lalu lanjutkan deployment kode terbaru. Migrasi mempertahankan tabel dan data tanggapan.
2. **Space**: folder `test-ai/` adalah repo terpisah (https://huggingface.co/spaces/rurisj/test-ai); push perubahan dari folder itu. Isi secret `API_KEY`, `HF_TOKEN`, dan `DATABASE_URL` pada Settings Space.
3. **Backend**: proyek Vercel baru, Root Directory `backend`. Isi environment variables seperti `backend/.env.example`.
4. **Frontend**: proyek Vercel baru, Root Directory `frontend`, isi `VITE_API_URL` dengan alamat backend. Setelah itu isi `FRONTEND_ORIGIN` di backend dengan alamat frontend, lalu deploy ulang backend.

Untuk database yang sudah digunakan, lakukan migrasi dan deployment saat aplikasi tidak menerima permintaan interpretasi: jalankan `migrasi_3.sql`, deploy Space, backend, dan frontend versi baru, lalu lakukan pengujian. Jangan jalankan `migrasi_2.sql` setelah `migrasi_3.sql`; file tersebut hanya disertakan sebagai catatan versi sebelumnya.

## Uji lokal

```
cd backend && pip install -r requirements.txt && uvicorn app:app --port 8000
cd frontend && cp .env.example .env && npm install && npm run dev
```

## Batas yang perlu diketahui

- Interpretasi (Llama) dan prediksi impor memakai antrean terpisah di Space, jadi impor baru tidak menunggu Llama.
- Pekerjaan yang tidak bergerak 30 menit ditandai gagal otomatis (`BATAS_MACET_MENIT`) dan bisa diulang dari tahap yang gagal.
- Masuk memakai satu kata sandi bersama (`ADMIN_PASSWORD`). Belum ada akun per pengguna.
- Fungsi Vercel menerima isi permintaan sekitar 4,5 MB, jadi berkas impor dibatasi sekitar 4 MB.

## Pembaruan struktur database interpretasi

Metode interpretasi terbaru menggunakan frekuensi kata dan frasa. Tabel `interpretation_runs` menyimpan `top_words`, `top_phrases`, `max_new_pola`, dan `max_new_saran`. Tabel `interpretation_stages` menyimpan rincian kata/frasa pada kolom `detail` (JSONB). Kolom lama `top_k`, `chunk_size`, `max_new_tokens`, `chunks_total`, dan `chunks_done` tidak digunakan lagi.

- Database baru: jalankan `backend/schema.sql`.
- Database lama yang sudah menjalankan skema/migrasi sebelumnya: jalankan `backend/migrasi_3.sql`.
- `migrasi_3.sql` mempertahankan tabel dan data; tidak menjalankan `DROP TABLE`.
- Deploy ulang Hugging Face Space, backend Vercel, dan frontend Vercel dari folder masing-masing setelah migrasi selesai.
