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

## 2. Panduan Lengkap Environment Variables (Frontend, Backend, & Hugging Face Spaces)

### Ringkasan Kecocokan Antar-Layanan (Variabel yang Wajib Sama)

| Pasangan Variabel | Lokasi 1 | Lokasi 2 | Aturan / Hint |
|---|---|---|---|
| **Kunci API Internal** | Backend: `SPACE_API_KEY` | HFS Secret: `API_KEY` | **Wajib sama persis.** Dipakai pada header `X-API-Key` saat Backend memanggil AI Service. |
| **Koneksi Database** | Backend: `DATABASE_URL` | HFS Secret: `DATABASE_URL` | **Wajib mengarah ke database Neon yang sama.** Format: `postgresql://USER:PASSWORD@HOST/neondb?sslmode=require`. |
| **Token Hugging Face** | Backend: `HF_SPACE_TOKEN` | HFS Secret: `HF_TOKEN` | Token akses Hugging Face (`hf_...`) yang **masih aktif (belum expired)**. Di Backend (`HF_SPACE_TOKEN`) wajib diisi jika Space berstatus **Private**. Di HFS (`HF_TOKEN`) wajib memiliki izin baca ke repo model Hybrid & `meta-llama/Llama-3.2-3B-Instruct`. |
| **Alamat Backend** | Frontend: `VITE_API_URL` | Domain Vercel Backend | Tanpa garis miring `/` di akhir (contoh: `https://arisza-backend.vercel.app`). |
| **Alamat Frontend (CORS)** | Backend: `FRONTEND_ORIGIN` | Domain Vercel Frontend | Tanpa garis miring `/` di akhir. Bisa lebih dari satu dipisahkan koma (contoh: `https://arisza-frontend.vercel.app,http://localhost:5173`). |

---

### A. Environment Variables Frontend (`frontend/.env` & Vercel Frontend)

Tempat pengaturan:
- **Production:** Vercel Dashboard → Project Frontend → **Settings → Environment Variables**
- **Lokal:** File `frontend/.env`

| Nama Variabel | Wajib? | Contoh Nilai Production (Vercel) | Contoh Nilai Lokal (`frontend/.env`) | Fungsi / Hint |
|---|---|---|---|---|
| `VITE_API_URL` | **Wajib** | `https://DOMAIN-BACKEND.vercel.app` | `http://127.0.0.1:8000` | URL tempat Backend FastAPI berjalan. Jangan tambahkan `/api` atau `/` di akhir. |

Contoh isi `frontend/.env` (lokal):
```env
VITE_API_URL=http://127.0.0.1:8000
```

Contoh isi di **Vercel Frontend** (production):
```env
VITE_API_URL=https://DOMAIN-BACKEND-VERCEL.vercel.app
```
> **Hint Frontend:** Jangan pernah memasukkan `SPACE_API_KEY`, `HF_SPACE_TOKEN`, `DATABASE_URL`, atau `SESSION_SECRET` ke Frontend karena seluruh variabel `VITE_*` dapat dilihat oleh publik di browser.

---

### B. Environment Variables Backend (`backend/.env` & Vercel Backend)

Tempat pengaturan:
- **Production:** Vercel Dashboard → Project Backend → **Settings → Environment Variables**
- **Lokal:** File `backend/.env`

| Nama Variabel | Wajib? | Contoh Nilai Production (Vercel) | Contoh Nilai Lokal (`backend/.env`) | Fungsi / Hint |
|---|---|---|---|---|
| `DATABASE_URL` | **Wajib** | `postgresql://USER:PASS@HOST/neondb?sslmode=require` | Sama dengan production | Connection string PostgreSQL Neon (harus sama dengan yang ada di HFS). |
| `SESSION_SECRET` | **Wajib** | String acak minimal 32 karakter | String acak minimal 32 karakter | Kunci penandatangan token login JWT. Buat dengan: `python -c "import secrets; print(secrets.token_urlsafe(48))"`. |
| `SPACE_URL` | **Wajib** | `https://rurisj-test-ai.hf.space` | `https://rurisj-test-ai.hf.space` (atau `http://127.0.0.1:7860` jika AI lokal) | Gunakan subdomain runtime `.hf.space` (tanpa `/health` di akhir). |
| `SPACE_API_KEY` | **Wajib** | String rahasia acak | Sama dengan production | **Harus sama persis** dengan Secret `API_KEY` di Hugging Face Space. |
| `HF_SPACE_TOKEN` | **Wajib jika Space Private** | `hf_xxxxxxxxxxxxxxxxxxxxxxxxx` | `hf_xxxxxxxxxxxxxxxxxxxxxxxxx` | User Access Token Hugging Face (`Read`) yang **masih aktif**. Jika token ini kedaluwarsa (*expired*) saat Space berstatus Private, HFS akan mengembalikan **HTTP 404 HTML**. |
| `FRONTEND_ORIGIN` | **Wajib** | `https://DOMAIN-FRONTEND.vercel.app` | `http://localhost:5173,http://127.0.0.1:5173` | Daftar domain Frontend yang diizinkan mengakses Backend (CORS), pisahkan dengan koma tanpa spasi. |
| `SESSION_TTL_SECONDS` | Opsional | `43200` | `43200` | Masa berlaku sesi login dalam detik (default `43200` = 12 jam). |
| `BATAS_MACET_MENIT` | Opsional | `30` | `30` | Batas waktu (menit) sebelum pekerjaan `queued`/`running` yang macet ditandai `failed` agar bisa diulang. |
| `MAKS_BARIS_IMPOR` | Opsional | `5000` | `5000` | Maksimum jumlah baris CSV yang dapat diimpor dalam satu kali unggah. |

Contoh salinan siap pakai untuk **Backend Vercel**:
```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST/neondb?sslmode=require
SESSION_SECRET=ISI_SECRET_ACAK_MINIMAL_32_KARAKTER
SPACE_URL=https://rurisj-test-ai.hf.space
SPACE_API_KEY=ISI_KUNCI_YANG_SAMA_DENGAN_API_KEY_DI_HFS
HF_SPACE_TOKEN=hf_ISI_TOKEN_HUGGINGFACE_AKTIF_JIKA_SPACE_PRIVATE
FRONTEND_ORIGIN=https://DOMAIN-FRONTEND-VERCEL.vercel.app
SESSION_TTL_SECONDS=43200
BATAS_MACET_MENIT=30
MAKS_BARIS_IMPOR=5000
```

---

### C. Environment Variables AI Service / Hugging Face Spaces (`test-ai`)

Tempat pengaturan:
- **Production:** Halaman Hugging Face Space (`rurisj/test-ai`) → **Settings → Variables and secrets → New secret** *(masukkan sebagai **Secret**, bukan Variable biasa agar nilainya terenkripsi dan tidak terjadi bentrok nama)*
- **Lokal (opsional):** File `test-ai/.env`

| Nama Secret | Wajib? | Contoh Nilai | Fungsi / Hint |
|---|---|---|---|
| `API_KEY` | **Wajib** | String rahasia acak | **Harus sama persis** dengan `SPACE_API_KEY` pada Backend Vercel. |
| `DATABASE_URL` | **Wajib** | `postgresql://USER:PASS@HOST/neondb?sslmode=require` | **Harus sama persis** dengan `DATABASE_URL` pada Backend Vercel. |
| `HF_TOKEN` | **Wajib** | `hf_xxxxxxxxxxxxxxxxxxxxxxxxx` | Token Hugging Face yang **masih aktif** dan memiliki izin akses baca ke repo model `rurisj/model-sentimen-hybridindobertbilstm` serta gated repo `meta-llama/Llama-3.2-3B-Instruct`. |

> **Hint HFS (`test-ai`):**
> - Jangan memasukkan `API_KEY`, `DATABASE_URL`, atau `HF_TOKEN` ke bagian **Variables** dan **Secrets** secara bersamaan dengan nama yang sama karena akan memicu `CONFIG_ERROR: Collision on variables and secrets names`. Gunakan bagian **Secrets** saja.
> - Parameter model dan pemrosesan **tidak perlu** dimasukkan ke ENV HFS karena sudah ditetapkan di `test-ai/app/config.py`:
>   - Model Llama: `meta-llama/Llama-3.2-3B-Instruct` (`bfloat16`)
>   - Kata & frasa teratas: masing-masing `10`
>   - Maksimal token pola opini: `220`, maksimal token saran: `280`
>   - Maksimal teks per permintaan prediksi: `200`, ukuran batch prediksi: `16`, riwayat pekerjaan: `50`

---

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

## 4. Hint Troubleshooting Error Umum (Backend ↔ HFS)

| Gejala / Pesan Error | Penyebab Utama | Solusi Cepat |
|---|---|---|
| `AI Service mengembalikan HTTP 404 ... Respons: <!DOCTYPE html>` | 1) Space berstatus **Private**, tetapi `HF_SPACE_TOKEN` di Backend Vercel belum diisi atau **sudah kedaluwarsa (*expired*)**.<br>2) `SPACE_URL` diisi URL halaman web `https://huggingface.co/spaces/...` bukan `https://NAMA-SPACE.hf.space`. | Perbarui `HF_SPACE_TOKEN` di Backend Vercel dengan Access Token Hugging Face (`hf_...`) yang masih aktif (atau ubah Space ke **Public**), pastikan `SPACE_URL=https://rurisj-test-ai.hf.space`, lalu **Redeploy** Backend Vercel. |
| `AI Service mengembalikan HTTP 401 ... Kunci API tidak valid` | Nilai `SPACE_API_KEY` di Backend Vercel tidak sama dengan Secret `API_KEY` di Hugging Face Space. | Samakan nilai `SPACE_API_KEY` (Backend) dan `API_KEY` (HFS Secret), lalu redeploy. |
| `hybrid_status: load_failed` (`401 Client Error` pada `/health`) | Secret `HF_TOKEN` di dalam Hugging Face Space sudah kedaluwarsa (*expired*) atau tidak punya akses ke repo model Hybrid/Llama. | Ganti Secret `HF_TOKEN` di Settings Hugging Face Space dengan Access Token Hugging Face yang aktif. |
| `CONFIG_ERROR: Collision on variables and secrets names` di HFS | Nama variabel yang sama (misal `HF_TOKEN`) didaftarkan di **Variables** sekaligus di **Secrets** pada HFS. | Hapus duplikatnya dari bagian **Variables**, dan simpan hanya di bagian **Secrets**. |
| `Tidak dapat terhubung ke AI Service` / `Connection refused` | Space sedang tidur (*Sleeping*), masih proses *Building*, atau `app_port` bukan `7860`. | Buka halaman Space di Hugging Face, pastikan statusnya **Running**, dan periksa tab **Logs / Container logs**. |
| Error CORS saat login dari Frontend Vercel | Domain Frontend Vercel belum dimasukkan ke `FRONTEND_ORIGIN` di Backend Vercel. | Isi `FRONTEND_ORIGIN=https://DOMAIN-FRONTEND.vercel.app` (tanpa `/` di akhir) pada Backend Vercel, lalu redeploy. |

Pemuatan model Hybrid dilakukan secara tertunda (*lazy loading*), sehingga kegagalan unduh atau muat bobot tidak menghentikan startup FastAPI. Jika pemuatan model gagal, endpoint `/health` tetap dapat diakses dan detail kegagalan dicatat pada field `hybrid_load_error` serta Logs Space.

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
