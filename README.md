# Sistem Analisis Sentimen Arisza Library & Learning

Panduan ini menjelaskan susunan production, konfigurasi Environment Variables, serta cara menjalankan frontend dan backend secara lokal. Pada deployment production, layanan AI tetap dijalankan di Hugging Face Spaces.

## 1. Arsitektur deployment

```text
Frontend React + Vite  -> Vercel
          |
          v  HTTP API
Backend FastAPI        -> Vercel
          |
          v  HTTP API
AI Service FastAPI     -> Hugging Face Spaces (test-ai)
  - Hybrid IndoBERT-BiLSTM -> bobot dari Hugging Face Model Hub
  - Llama 3.2 3B Instruct -> model Meta melalui Hugging Face Model Hub
          |
          v
PostgreSQL             -> Neon
```

Backend dan AI Service menggunakan database Neon yang sama. Frontend tidak menyimpan API key, token Hugging Face, URL database, atau session secret.

## 2. Environment Variables production

### Frontend Vercel

```env
VITE_API_URL=https://DOMAIN-BACKEND-VERCEL
```

### Backend Vercel

```env
DATABASE_URL=URL_DATABASE_NEON
SESSION_SECRET=SECRET_ACAK_MINIMAL_32_KARAKTER
SPACE_URL=https://NAMA-SPACE.hf.space
SPACE_API_KEY=KUNCI_YANG_SAMA_DENGAN_API_KEY_AI_SPACE
FRONTEND_ORIGIN=https://DOMAIN-FRONTEND-VERCEL
```

Konfigurasi tambahan yang memiliki nilai bawaan dan dapat diatur bila diperlukan:

```env
SESSION_TTL_SECONDS=43200
BATAS_MACET_MENIT=30
MAKS_BARIS_IMPOR=5000
```

`HF_SPACE_TOKEN` hanya diperlukan jika Hugging Face Space bersifat private. Jangan memasukkan rahasia ke frontend.

### Hugging Face Spaces (`test-ai`)

Pada **Settings → Variables and secrets**, tambahkan tiga Secrets:

| Secret | Isi |
|---|---|
| `API_KEY` | Harus sama dengan `SPACE_API_KEY` pada backend Vercel. |
| `DATABASE_URL` | URL Neon yang sama dengan backend. |
| `HF_TOKEN` | Token Hugging Face dengan akses ke model Llama 3.2 dan repository bobot Hybrid jika repository tersebut private. |

Parameter model dan pemrosesan tidak perlu dimasukkan ke ENV. Semua sudah ditetapkan di `test-ai/app/config.py`:

- Model Llama: `meta-llama/Llama-3.2-3B-Instruct`.
- Dtype: `bfloat16`.
- Kata dan frasa teratas: masing-masing 10.
- Maksimal token pola opini: 220.
- Maksimal token saran: 280.
- Maksimal teks per permintaan prediksi: 200.
- Ukuran batch prediksi: 16.
- Riwayat pekerjaan: 50.

## 3. Deploy atau memperbarui AI Service

Folder `test-ai` merupakan isi repository Hugging Face Space. Jika memperbarui Space melalui Git, salin/push **isi folder `test-ai` ke root repository Space**, sehingga `Dockerfile`, `README.md`, `requirements.txt`, dan folder `app/` berada di root repository Space.

Space menggunakan Docker dengan port `7860`. Perintah startup pada `Dockerfile` adalah:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

Setelah build selesai, uji alamat berikut:

- `https://NAMA-SPACE.hf.space/health`
- `https://NAMA-SPACE.hf.space/docs`

Endpoint `/health` harus mengembalikan `status: ok`. Sebelum klasifikasi pertama, `hybrid_status: not_loaded` adalah normal karena bobot Hybrid dimuat saat pertama kali diperlukan. Llama juga dimuat ketika interpretasi pertama diminta.

## 4. Penanganan `Connection refused`

Jika backend menampilkan `Gagal menghubungi layanan AI` atau `Connection refused`, periksa secara berurutan:

1. Buka `SPACE_URL/health` secara langsung. Gunakan format `https://NAMA-SPACE.hf.space`, bukan URL halaman `https://huggingface.co/spaces/...`.
2. Pastikan status Space **Running** dan proses build berhasil.
3. Periksa **Logs** dan **Container logs** pada Space. Pastikan tidak ada kegagalan instalasi dependensi atau startup Uvicorn.
4. Pastikan Docker menjalankan Uvicorn pada `0.0.0.0:7860` dan metadata Space menyatakan `app_port: 7860`.
5. Pastikan `SPACE_API_KEY` pada backend sama persis dengan Secret `API_KEY` pada Space.
6. Jika Space private, isi `HF_SPACE_TOKEN` pada backend dengan token yang memiliki akses ke Space tersebut.
7. Setelah mengubah Environment Variables Vercel, lakukan redeploy backend.

Pemuatan model Hybrid dilakukan secara tertunda (lazy loading), sehingga kegagalan unduh atau muat bobot tidak lagi menghentikan startup FastAPI. Jika pemuatan model gagal, endpoint `/health` tetap dapat diakses dan detail kegagalan dicatat pada Logs Space.

## 5. Persiapan database Neon

Backend dan AI Service harus menggunakan `DATABASE_URL` yang mengarah ke database Neon yang sama.

### Database baru

1. Buat database PostgreSQL di Neon.
2. Buka SQL Editor.
3. Jalankan seluruh isi `backend/schema.sql` satu kali.
4. Buat akun pertama setelah backend lokal siap, atau gunakan mekanisme pengelolaan akun yang sudah tersedia.

### Database lama

1. Hentikan sementara backend dan AI Service serta pastikan tidak ada pekerjaan impor/interpretasi yang sedang berjalan.
2. Buat backup database.
3. Jalankan `backend/migrasi_penamaan_tabel.sql` satu kali.
4. Jalankan `backend/schema.sql`.
5. Buat akun pertama menggunakan `backend/create_user.py`. Skrip mengaitkan data lama yang belum memiliki `user_id` ke akun pertama, lalu menetapkan kolom tersebut sebagai wajib.

Jangan menjalankan migrasi penamaan pada database baru yang sudah menggunakan nama tabel terbaru. Jika tabel lama dan baru sama-sama ditemukan, hentikan proses dan periksa database terlebih dahulu.

## 6. Development lokal: frontend dan backend

Development lokal dapat menggunakan AI Service production di Hugging Face Spaces. Dengan cara ini, laptop tidak perlu memuat model Hybrid atau Llama.

### Persyaratan

- Python 3.10 atau lebih baru.
- Node.js 20 atau lebih baru dan npm.
- Git.
- Database Neon yang sudah disiapkan.

### Backend

Dari folder `backend`, buat environment dan instal dependensi:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Isi `backend/.env` dengan `DATABASE_URL`, `SESSION_SECRET`, `SPACE_URL` (alamat Hugging Face Space production), `SPACE_API_KEY`, dan `FRONTEND_ORIGIN=http://localhost:5173`. `HF_SPACE_TOKEN` hanya diisi jika Space private.

Jalankan backend:

```powershell
uvicorn app:app --reload --env-file .env --host 127.0.0.1 --port 8000
```

Periksa `http://127.0.0.1:8000/api/health` dan `http://127.0.0.1:8000/docs`.

Untuk membuat akun pertama, pastikan schema/migrasi sudah selesai, lalu jalankan dari folder `backend`:

```powershell
python create_user.py --email pengelola@arisza.id
```

Masukkan kata sandi minimal 12 karakter saat diminta.

### Frontend

Dari folder `frontend`:

```powershell
Copy-Item .env.example .env
npm install
```

Pastikan `frontend/.env` berisi:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Jalankan:

```powershell
npm run dev
```

Buka `http://localhost:5173`.

### Menjalankan AI Service secara lokal (opsional)

Langkah ini hanya diperlukan jika ingin mengembangkan AI Service tanpa Hugging Face Spaces. Buat environment Python terpisah pada folder `test-ai`, instal PyTorch CPU dan dependensi, lalu isi `test-ai/.env` berdasarkan `.env.example`. Jika AI Service lokal digunakan, ubah `SPACE_URL` pada `backend/.env` menjadi `http://127.0.0.1:7860`.

```powershell
cd test-ai
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --env-file .env --host 127.0.0.1 --port 7860
```

Menjalankan Llama 3.2 3B secara lokal memerlukan RAM yang cukup besar. Untuk penggunaan normal, pertahankan AI Service di Hugging Face Spaces.

## 7. Pengujian

AI Service:

```powershell
cd test-ai
python -m unittest discover -s tests -v
```

Backend:

```powershell
cd backend
python -m unittest discover -s tests -v
```

Build frontend:

```powershell
cd frontend
npm run build
```

## 8. File lokal yang tidak diunggah ke GitHub

`.gitignore` mengecualikan `.venv/`, `venv/`, `node_modules/`, `.env`, cache Python, cache model, bobot model unduhan, hasil build, dan file log. File `.env.example` tetap dapat diunggah karena hanya berisi contoh konfigurasi. Jangan pernah commit file `.env` atau token rahasia.
