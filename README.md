# Sistem Analisis Sentimen Arisza Library & Learning

Panduan ini menjelaskan persiapan database, konfigurasi, dan cara menjalankan frontend, backend, serta AI Service (`test-ai`) secara lokal.

## 1. Komponen sistem

```text
frontend/  React + Vite       -> antarmuka web (lokal: http://localhost:5173)
backend/   FastAPI            -> API aplikasi (lokal: http://127.0.0.1:8000)
test-ai/   FastAPI + Hybrid   -> klasifikasi dan interpretasi (lokal: http://127.0.0.1:7860)
PostgreSQL                   -> database Neon
```

Frontend mengirim permintaan ke backend. Backend mengelola autentikasi, impor, dan penyajian data, kemudian memanggil AI Service. AI Service menjalankan Hybrid IndoBERT-BiLSTM, membuat Word Cloud, dan menjalankan interpretasi Llama 3.2. Backend dan AI Service menggunakan database Neon yang sama.

## 2. Persyaratan awal

Siapkan perangkat lunak berikut:

- Python 3.11 (disarankan untuk kompatibilitas dependensi AI).
- Node.js 20 atau lebih baru dan npm.
- Git.
- Akun PostgreSQL Neon.
- Akun Hugging Face. Untuk menjalankan interpretasi Llama 3.2, akun harus sudah memperoleh akses/menyetujui ketentuan model `meta-llama/Llama-3.2-3B-Instruct`.
- Koneksi internet untuk mengunduh dependensi dan bobot model.

Perintah di bawah menggunakan **Windows PowerShell**. Jika aktivasi virtual environment diblokir oleh kebijakan PowerShell, jalankan sekali pada terminal tersebut:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 3. Struktur folder

```text
arisza-sistem/
├── backend/
│   ├── app.py
│   ├── security.py
│   ├── create_user.py
│   ├── schema.sql
│   ├── migrasi_penamaan_tabel.sql
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   ├── package.json
│   └── .env.example
├── test-ai/
│   ├── app/
│   ├── model/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
└── README.md
```

Setiap komponen Python menggunakan virtual environment sendiri agar dependensinya tidak saling mengganggu.

## 4. Persiapan database Neon

Backend dan AI Service harus menggunakan `DATABASE_URL` yang mengarah ke database Neon yang sama.

### Database baru

1. Buat database PostgreSQL di Neon.
2. Buka SQL Editor.
3. Jalankan seluruh isi `backend/schema.sql` satu kali.
4. Lanjutkan ke bagian pembuatan akun pengguna setelah konfigurasi backend selesai.

### Database lama yang masih menggunakan nama tabel sebelumnya

1. Hentikan sementara backend dan AI Service. Pastikan tidak ada proses impor atau interpretasi yang sedang berjalan.
2. Buat backup database.
3. Jalankan `backend/migrasi_penamaan_tabel.sql` satu kali.
4. Jalankan `backend/schema.sql`.
5. Buat akun pertama menggunakan `backend/create_user.py`. Skrip akan mengaitkan data impor dan interpretasi lama yang belum memiliki `user_id` ke akun pertama, lalu menetapkan kolom tersebut sebagai wajib.

Jangan menjalankan migrasi penamaan pada database baru yang sudah menggunakan nama tabel terbaru. Jika tabel lama dan baru sama-sama ditemukan, hentikan proses dan periksa database terlebih dahulu.

## 5. Konfigurasi dan menjalankan AI Service (`test-ai`)

AI Service harus dijalankan lebih dahulu agar backend dapat mengirim pekerjaan klasifikasi dan interpretasi.

### 5.1 Buat virtual environment

Buka terminal PowerShell pertama:

```powershell
cd test-ai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

### 5.2 Instal PyTorch CPU dan dependensi

PyTorch dipasang terpisah agar sesuai dengan perangkat. Untuk menjalankan secara CPU pada Windows:

```powershell
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

Jika menggunakan GPU NVIDIA, pasang versi PyTorch yang sesuai dengan versi CUDA pada perangkat dari petunjuk resmi PyTorch, lalu jalankan `pip install -r requirements.txt`.

### 5.3 Buat dan isi `.env`

```powershell
Copy-Item .env.example .env
```

Buka `test-ai/.env`, lalu isi sekurang-kurangnya:

```env
API_KEY=KUNCI_RAHASIA_YANG_DIBUAT_SENDIRI
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
HF_TOKEN=hf_TOKEN_HUGGING_FACE_MILIK_KAMU
LLAMA_MODEL_ID=meta-llama/Llama-3.2-3B-Instruct
LLAMA_DTYPE=float32
```

- `API_KEY` adalah kunci komunikasi backend dengan AI Service. Nilainya harus sama dengan `SPACE_API_KEY` pada `backend/.env`.
- `DATABASE_URL` harus sama dengan URL database Neon yang digunakan backend.
- `HF_TOKEN` diperlukan ketika interpretasi Llama dijalankan. Pastikan akun Hugging Face telah memperoleh akses ke model Llama 3.2.
- `LLAMA_DTYPE=float32` lebih kompatibel untuk CPU, tetapi membutuhkan memori besar. Untuk perangkat yang mendukung bfloat16 atau GPU, dtype dapat disesuaikan.

Buat kunci acak dengan perintah berikut jika diperlukan:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Salin hasilnya ke `API_KEY` dan gunakan nilai yang sama untuk `SPACE_API_KEY` pada backend.

### 5.4 Jalankan AI Service

Tetap dari folder `test-ai` dan pastikan virtual environment aktif:

```powershell
uvicorn app.main:app --reload --env-file .env --host 127.0.0.1 --port 7860
```

Periksa layanan melalui browser:

- Health check: `http://127.0.0.1:7860/health`
- Dokumentasi API: `http://127.0.0.1:7860/docs`

Saat pertama kali dijalankan, bobot Hybrid IndoBERT-BiLSTM akan diunduh dari Hugging Face Hub ke cache lokal. Proses ini memerlukan koneksi internet dan ruang penyimpanan. Model Llama dimuat saat interpretasi pertama dijalankan, bukan ketika server mulai.

**Catatan kebutuhan perangkat:** Llama 3.2 3B cukup berat untuk dijalankan secara lokal. Jika RAM/perangkat tidak memadai, tetap jalankan AI Service pada Hugging Face Spaces. Dalam kondisi itu, lewati langkah menjalankan `test-ai` lokal dan ubah `SPACE_URL` backend ke alamat Space seperti dijelaskan pada bagian konfigurasi backend.

## 6. Konfigurasi dan menjalankan backend

Buka **terminal PowerShell kedua** agar AI Service tetap berjalan pada terminal pertama.

### 6.1 Buat virtual environment

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 6.2 Buat dan isi `.env`

```powershell
Copy-Item .env.example .env
```

Buka `backend/.env`, kemudian isi:

```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
SESSION_SECRET=SECRET_ACAK_MINIMAL_32_KARAKTER
SESSION_TTL_SECONDS=43200
SPACE_URL=http://127.0.0.1:7860
SPACE_API_KEY=SAMA_DENGAN_API_KEY_TEST_AI
HF_SPACE_TOKEN=
FRONTEND_ORIGIN=http://localhost:5173,http://127.0.0.1:5173
BATAS_MACET_MENIT=30
MAKS_BARIS_IMPOR=5000
```

Keterangan:

- `DATABASE_URL`: URL Neon yang sama dengan AI Service.
- `SESSION_SECRET`: secret khusus penandatanganan token login. Buat nilai acak dengan perintah:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

- `SPACE_URL`: gunakan `http://127.0.0.1:7860` jika AI Service berjalan lokal.
- `SPACE_API_KEY`: harus sama persis dengan `API_KEY` di `test-ai/.env`.
- `HF_SPACE_TOKEN`: kosongkan untuk AI Service lokal. Isi hanya jika backend mengakses Hugging Face Space private.
- `FRONTEND_ORIGIN`: alamat frontend lokal.

### 6.3 Buat akun pengguna pertama

Pastikan schema database sudah dibuat atau migrasi database lama sudah selesai. Skrip otomatis membaca `backend/.env`, sehingga tidak perlu menempelkan `DATABASE_URL` pada terminal.

```powershell
python create_user.py --email pengelola@arisza.id
```

Masukkan kata sandi dua kali ketika diminta. Kata sandi minimal 12 karakter dan disimpan sebagai hash PBKDF2-HMAC-SHA256. Untuk menambahkan akun lain, jalankan kembali perintah dengan email berbeda.

### 6.4 Jalankan backend

```powershell
uvicorn app:app --reload --env-file .env --host 127.0.0.1 --port 8000
```

Periksa melalui browser:

- Health check: `http://127.0.0.1:8000/api/health`
- Dokumentasi API: `http://127.0.0.1:8000/docs`

## 7. Menjalankan frontend

Buka **terminal PowerShell ketiga**.

```powershell
cd frontend
Copy-Item .env.example .env
npm install
```

Pastikan `frontend/.env` berisi:

```env
VITE_API_URL=http://127.0.0.1:8000
```

Jalankan frontend:

```powershell
npm run dev
```

Buka alamat yang ditampilkan Vite, biasanya `http://localhost:5173`. Login menggunakan email dan kata sandi yang telah dibuat pada langkah backend.

Jika alamat backend atau frontend diubah, sesuaikan `VITE_API_URL` dan `FRONTEND_ORIGIN`, kemudian restart server terkait.

## 8. Urutan menjalankan sistem setiap kali development

Setelah pemasangan awal selesai, setiap kali ingin menggunakan sistem secara lokal:

1. Buka terminal pertama, masuk ke `test-ai`, aktifkan `.venv`, lalu jalankan AI Service pada port `7860`.
2. Buka terminal kedua, masuk ke `backend`, aktifkan `.venv`, lalu jalankan backend pada port `8000`.
3. Buka terminal ketiga, masuk ke `frontend`, lalu jalankan `npm run dev` pada port `5173`.
4. Buka `http://localhost:5173` dan login.

Contoh perintah untuk mengaktifkan kembali environment yang sudah dibuat:

```powershell
# Terminal test-ai
cd test-ai
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --env-file .env --host 127.0.0.1 --port 7860

# Terminal backend
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app:app --reload --env-file .env --host 127.0.0.1 --port 8000

# Terminal frontend
cd frontend
npm run dev
```

## 9. Pengujian setelah instalasi

Jalankan pengujian unit dari folder masing-masing.

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

AI Service:

```powershell
cd test-ai
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

Pemeriksaan build frontend:

```powershell
cd frontend
npm run build
```

Uji koneksi model AI (opsional, dari folder `test-ai`):

```powershell
python smoke_test.py http://127.0.0.1:7860 API_KEY_KAMU --tanpa-llama
```

Hapus opsi `--tanpa-llama` jika ingin menguji interpretasi Llama. Pengujian interpretasi memerlukan akses model dan memori perangkat yang memadai.

## 10. File development lokal yang tidak boleh ikut ke GitHub

File `.gitignore` pada root dan masing-masing komponen sudah disiapkan untuk mengecualikan file sementara dan rahasia. Contohnya:

| File/folder | Keterangan |
|---|---|
| `.venv/`, `venv/` | Virtual environment Python. |
| `node_modules/` | Dependensi frontend hasil `npm install`. |
| `.env`, `.env.local`, `.env.production` | Konfigurasi lokal dan kredensial. |
| `__pycache__/`, `*.pyc` | Cache Python. |
| `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` | Cache alat pengujian dan pemeriksaan kode. |
| `dist/`, `build/` | Hasil build. |
| `*.pt`, `*.pth`, `*.safetensors`, `*.ckpt` | Bobot model yang diunduh atau dihasilkan. |
| `.cache/`, `hf_cache/` | Cache model dan unduhan. |
| `*.log`, `*.tmp` | Log dan file sementara. |

File `.env.example` tetap boleh di-commit karena hanya berisi nama variabel dan contoh nilai, bukan kredensial asli. Jangan pernah memasukkan password database, API key, HF token, atau session secret asli ke GitHub.

Untuk memeriksa file yang diabaikan Git:

```powershell
git check-ignore -v backend/.venv backend/.env frontend/node_modules frontend/.env test-ai/.venv test-ai/.env
```

Jika file rahasia pernah terlanjur di-commit, menambahkan `.gitignore` saja tidak menghapusnya dari riwayat Git. Hapus file dari tracking dan rotasi/ganti kredensial yang sudah terlanjur terekspos.

## 11. Konfigurasi jika AI Service tetap di Hugging Face Spaces

Jika perangkat lokal tidak cukup kuat menjalankan Llama 3.2, backend dan frontend tetap dapat dijalankan lokal sementara AI Service tetap berada di Hugging Face Spaces.

Pada `backend/.env`, ubah:

```env
SPACE_URL=https://USERNAME-NAMA-SPACE.hf.space
SPACE_API_KEY=SAMA_DENGAN_SECRET_API_KEY_DI_SPACE
HF_SPACE_TOKEN=
```

Isi `API_KEY`, `HF_TOKEN`, dan `DATABASE_URL` pada Secrets Hugging Face Space. Jika Space private, isi `HF_SPACE_TOKEN` pada backend dengan token yang memiliki akses ke Space. Dalam mode ini, tidak perlu menjalankan `test-ai` lokal.

## 12. Catatan operasional

- Backend dan AI Service harus menunjuk ke database Neon yang sama.
- Model Hybrid diunduh otomatis dari Hugging Face Hub ketika AI Service pertama kali dijalankan dan file bobot belum tersedia secara lokal.
- Interpretasi Llama dijalankan saat fitur interpretasi digunakan; pemuatan model pertama dapat memerlukan waktu.
- Sistem menggunakan satu ruang data analisis bersama untuk akun yang terdaftar. `user_id` mencatat akun pelaksana impor dan interpretasi, bukan memisahkan data berdasarkan akun.
- Akun dibuat melalui `backend/create_user.py`; sistem belum menyediakan pendaftaran akun publik.
- Untuk deployment, gunakan Environment Variables pada Vercel dan Secrets pada Hugging Face Spaces. Jangan mengunggah file `.env` lokal.
