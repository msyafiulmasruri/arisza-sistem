"""Backend sistem web Arisza (FastAPI di Vercel).

Tugasnya tipis: menerima impor, mencatat permintaan di PostgreSQL, memanggil layanan AI di
Hugging Face Space, lalu membaca hasil dari basis data. Model tidak dijalankan di sini.
"""
import csv
import io
import os
import re
import time
from contextlib import contextmanager

import httpx
import psycopg
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from psycopg.rows import dict_row

from security import create_access_token, verify_access_token, verify_password

DATABASE_URL = os.getenv("DATABASE_URL", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", "")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "43200"))
SPACE_URL = os.getenv("SPACE_URL", "").rstrip("/")
SPACE_API_KEY = os.getenv("SPACE_API_KEY", "")
HF_SPACE_TOKEN = os.getenv("HF_SPACE_TOKEN", "")
FRONTEND_ORIGINS = [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if o.strip()]
BATAS_MACET_MENIT = int(os.getenv("BATAS_MACET_MENIT", "30"))
MAKS_BARIS_IMPOR = int(os.getenv("MAKS_BARIS_IMPOR", "5000"))

KOLOM_TEKS = {"text", "teks", "komentar", "ulasan", "review", "comment", "tanggapan", "isi"}
KOLOM_MEDIA = {"media", "sumber", "platform", "source"}
TAHAP = ["positive", "neutral", "negative", "saran"]
LABEL = {"positive", "neutral", "negative"}

app = FastAPI(title="Arisza Backend")
app.add_middleware(
    CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_methods=["*"], allow_headers=["*"],
)


# ---------- dasar ----------

class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


@contextmanager
def konek():
    if not DATABASE_URL:
        raise HTTPException(503, "DATABASE_URL belum diatur di backend.")
    conn = psycopg.connect(
        DATABASE_URL, row_factory=dict_row, autocommit=True, prepare_threshold=None, connect_timeout=10
    )
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(authorization: str = Header(default="")):
    if not SESSION_SECRET or len(SESSION_SECRET) < 32:
        raise HTTPException(503, "SESSION_SECRET belum diatur atau kurang dari 32 karakter.")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(401, "Sesi tidak ditemukan. Silakan login kembali.")
    payload = verify_access_token(token.strip(), SESSION_SECRET)
    if payload is None:
        raise HTTPException(401, "Sesi tidak valid atau telah kedaluwarsa. Silakan login kembali.")
    with konek() as conn:
        user = conn.execute(
            "select id, email from users where id=%s", (int(payload["sub"]),)
        ).fetchone()
    if user is None:
        raise HTTPException(401, "Akun tidak ditemukan. Silakan login kembali.")
    return user


def panggil_space(path, payload):
    if not SPACE_URL or not SPACE_API_KEY:
        raise RuntimeError("SPACE_URL atau SPACE_API_KEY belum diatur di backend Vercel.")
    headers = {"X-API-Key": SPACE_API_KEY}
    if HF_SPACE_TOKEN:
        headers["Authorization"] = f"Bearer {HF_SPACE_TOKEN}"

    # Ulangi koneksi singkat untuk mengatasi Space yang baru bangun/restart.
    # Permintaan ke endpoint jobs hanya mendaftarkan pekerjaan dan seharusnya cepat.
    url = f"{SPACE_URL}{path}"
    for percobaan in range(2):
        try:
            r = httpx.post(
                url, json=payload, headers=headers,
                timeout=httpx.Timeout(8.0, connect=3.0),
            )
            if r.status_code in (502, 503, 504) and percobaan < 1:
                time.sleep(1)
                continue
            r.raise_for_status()
            return
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            if percobaan < 1:
                time.sleep(1)
                continue
            raise RuntimeError(
                f"Tidak dapat terhubung ke AI Service ({SPACE_URL}). "
                "Pastikan Space sudah Running, URL SPACE_URL benar (https://NAMA-SPACE.hf.space), "
                "dan aplikasi di Space mendengarkan port 7860. Periksa Logs/Container logs Hugging Face. "
                f"Detail koneksi: {type(exc).__name__}: {exc}"
            ) from exc
        except httpx.HTTPStatusError as exc:
            isi = (exc.response.text or "").strip().replace("\n", " ")[:250]
            raise RuntimeError(
                f"AI Service mengembalikan HTTP {exc.response.status_code}. "
                f"Periksa API_KEY, akses Space, dan log layanan. Respons: {isi}"
            ) from exc


def tandai_macet(conn):
    """Pekerjaan yang tidak bergerak lama (Space restart atau tidur) ditandai gagal agar bisa diulang."""
    pesan = "Proses terhenti karena melewati batas waktu. Gunakan tombol ulangi."
    ids = [
        r["id"]
        for r in conn.execute(
            "update interpretations set status='failed', error=%s, updated_at=now() "
            "where status in ('queued','running') and updated_at < now() - make_interval(mins => %s) returning id",
            (pesan, BATAS_MACET_MENIT),
        ).fetchall()
    ]
    if ids:
        conn.execute(
            "update interpretation_results set status='failed', error=%s where interpretation_id = any(%s) and status='running'",
            (pesan, ids),
        )
    conn.execute(
        "update batches set status='failed', error=%s, updated_at=now() "
        "where status in ('queued','running') and updated_at < now() - make_interval(mins => %s)",
        (pesan, BATAS_MACET_MENIT),
    )


def muat_interpretasi(conn, interpretation_id):
    run = conn.execute("select * from interpretations where id=%s", (interpretation_id,)).fetchone()
    if run is None:
        return None
    tahap = conn.execute("select * from interpretation_results where interpretation_id=%s", (interpretation_id,)).fetchall()
    run["tahap"] = sorted(tahap, key=lambda t: TAHAP.index(t["stage"]))
    return run


# ---------- umum ----------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(body: LoginRequest):
    if not SESSION_SECRET or len(SESSION_SECRET) < 32:
        raise HTTPException(503, "SESSION_SECRET belum diatur atau kurang dari 32 karakter.")
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(401, "Email atau kata sandi tidak sesuai.")
    with konek() as conn:
        user = conn.execute(
            "select id, email, password_hash from users where email=%s", (email,)
        ).fetchone()
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Email atau kata sandi tidak sesuai.")
    token = create_access_token(user["id"], user["email"], SESSION_SECRET, SESSION_TTL_SECONDS)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": SESSION_TTL_SECONDS,
        "user": {"id": user["id"], "email": user["email"]},
    }


@app.get("/api/auth/me")
def auth_me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"]}


# ---------- impor ----------

def baca_berkas(nama, isi):
    nama = (nama or "").lower()
    if nama.endswith(".csv"):
        teks = isi.decode("utf-8-sig", errors="replace")
        try:
            dialek = csv.Sniffer().sniff(teks[:4096], delimiters=",;\t")
        except csv.Error:
            dialek = csv.excel
        return [list(r) for r in csv.reader(io.StringIO(teks), dialek)]
    if nama.endswith(".xlsx"):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(isi), read_only=True, data_only=True)
        return [list(r) for r in wb.active.iter_rows(values_only=True)]
    raise HTTPException(400, "Format berkas harus .csv atau .xlsx.")


def rapikan_media(nama):
    return " ".join(str(nama).split())


@app.post("/api/import", status_code=202)
async def impor(
    file: UploadFile = File(...), media_bawaan: str = Form(""),
    user: dict = Depends(get_current_user),
):
    baris = baca_berkas(file.filename, await file.read())
    if len(baris) < 2:
        raise HTTPException(400, "Berkas kosong atau hanya berisi judul kolom.")
    judul = [str(h or "").strip().lower() for h in baris[0]]
    kt = next((i for i, h in enumerate(judul) if h in KOLOM_TEKS), None)
    km = next((i for i, h in enumerate(judul) if h in KOLOM_MEDIA), None)
    if kt is None:
        raise HTTPException(
            400, "Kolom teks tidak ditemukan. Beri judul kolom salah satu dari: " + ", ".join(sorted(KOLOM_TEKS)) + "."
        )
    media_bawaan = rapikan_media(media_bawaan)
    if km is None and not media_bawaan:
        raise HTTPException(400, "Berkas tidak punya kolom media. Isi kolom 'media' atau tulis nama media pada formulir.")

    with konek() as conn:
        ada = {r["media"].lower(): r["media"] for r in conn.execute("select distinct media from responses").fetchall()}
        data = []
        for r in baris[1:]:
            teks = str(r[kt]).strip() if kt < len(r) and r[kt] is not None else ""
            media = rapikan_media(r[km]) if km is not None and km < len(r) and r[km] else media_bawaan
            if not teks or not media:
                continue
            media = ada.setdefault(media.lower(), media)
            data.append((media, teks))
        if not data:
            raise HTTPException(400, "Tidak ada baris yang berisi teks dan media.")
        if len(data) > MAKS_BARIS_IMPOR:
            raise HTTPException(400, f"Maksimal {MAKS_BARIS_IMPOR} baris per berkas; bagi berkas menjadi beberapa bagian.")

        batch = conn.execute(
            "insert into batches (user_id, filename, total) values (%s, %s, %s) returning id",
            (user["id"], file.filename, len(data)),
        ).fetchone()
        with conn.cursor() as cur:
            cur.executemany(
                "insert into responses (batch_id, media, text) values (%s, %s, %s)",
                [(batch["id"], m, t) for m, t in data],
            )
        kirim_batch(conn, batch["id"])
        return conn.execute("select * from batches where id=%s", (batch["id"],)).fetchone()


def kirim_batch(conn, batch_id):
    try:
        panggil_space("/jobs/classify", {"batch_id": batch_id})
    except Exception as exc:
        conn.execute(
            "update batches set status='failed', error=%s, updated_at=now() where id=%s",
            (f"Gagal menghubungi layanan AI: {exc}"[:500], batch_id),
        )


@app.get("/api/batches", dependencies=[Depends(get_current_user)])
def daftar_batch():
    with konek() as conn:
        tandai_macet(conn)
        return conn.execute(
            "select b.*, count(r.id) filter (where r.status<>'pending') as diproses "
            "from batches b left join responses r on r.batch_id=b.id "
            "group by b.id order by b.id desc limit 10"
        ).fetchall()


@app.post("/api/batches/{batch_id}/retry", dependencies=[Depends(get_current_user)], status_code=202)
def ulangi_batch(batch_id: int):
    with konek() as conn:
        b = conn.execute("select status from batches where id=%s", (batch_id,)).fetchone()
        if b is None:
            raise HTTPException(404, "Batch tidak ditemukan.")
        if b["status"] != "failed":
            raise HTTPException(409, "Hanya batch yang gagal yang bisa diulang.")
        conn.execute("update batches set status='queued', error=null, updated_at=now() where id=%s", (batch_id,))
        kirim_batch(conn, batch_id)
        return conn.execute("select * from batches where id=%s", (batch_id,)).fetchone()


# ---------- dasbor ----------

@app.get("/api/summary", dependencies=[Depends(get_current_user)])
def ringkasan():
    with konek() as conn:
        tandai_macet(conn)
        media = conn.execute(
            "select media, "
            "count(*) filter (where status='ok') as total, "
            "count(*) filter (where label='positive') as positive, "
            "count(*) filter (where label='neutral') as neutral, "
            "count(*) filter (where label='negative') as negative, "
            "count(*) filter (where status='pending') as pending, "
            "count(*) filter (where status='ok' and (clean_text is null or wc_text is null)) as perlu_lengkap "
            "from responses group by media order by media"
        ).fetchall()
        terbaru = {
            r["media"]: r
            for r in conn.execute(
                "select distinct on (media) id, media, status, error from interpretations order by media, id desc"
            ).fetchall()
        }
        selesai = {
            r["media"]: r
            for r in conn.execute(
                "select distinct on (r.media) r.id, r.media, r.n_texts, r.finished_at, "
                "(select sum(s.duration) from interpretation_results s where s.interpretation_id = r.id) as total_detik, "
                "(select count(*) = 4 and bool_and(coalesce(s.detail->>'metode' = 'frekuensi_v1', false)) "
                " from interpretation_results s where s.interpretation_id = r.id) as metode_frekuensi "
                "from interpretations r where r.status='done' order by r.media, r.id desc"
            ).fetchall()
        }
        for m in media:
            t, s = terbaru.get(m["media"]), selesai.get(m["media"])
            m["interpretasi"] = {
                "status": t["status"] if t else None,
                "interpretation_id": t["id"] if t else None,
                "selesai_pada": s["finished_at"] if s else None,
                "total_detik": float(s["total_detik"]) if s and s["total_detik"] is not None else None,
                "n_teks": s["n_texts"] if s else None,
                "ada_hasil": s is not None,
                # data bertambah sejak interpretasi terakhir
                "basi": bool(s) and (s["n_texts"] != m["total"] or not s["metode_frekuensi"]),
            }
        return media


@app.get("/api/media/{media}/wordclouds", dependencies=[Depends(get_current_user)])
def info_wordcloud(media: str):
    """Keterangan Word Cloud yang tersedia (gambarnya diambil lewat endpoint terpisah)."""
    with konek() as conn:
        return conn.execute(
            "select label, n_texts, updated_at from wordclouds where media=%s order by label", (media,)
        ).fetchall()


@app.get("/api/media/{media}/wordcloud/{label}", dependencies=[Depends(get_current_user)])
def gambar_wordcloud(media: str, label: str):
    if label not in LABEL:
        raise HTTPException(404, "Sentimen tidak dikenal.")
    with konek() as conn:
        r = conn.execute("select image from wordclouds where media=%s and label=%s", (media, label)).fetchone()
    if r is None:
        raise HTTPException(404, "Word Cloud belum tersedia.")
    return Response(bytes(r["image"]), media_type="image/png", headers={"Cache-Control": "no-store"})


@app.post("/api/maintenance/lengkapi", dependencies=[Depends(get_current_user)], status_code=202)
def lengkapi_data_lama():
    """Minta Space mengisi teks preprocessing dan Word Cloud untuk data lama (label tidak diubah)."""
    try:
        panggil_space("/jobs/complete", {})
    except Exception as exc:
        raise HTTPException(502, f"Gagal menghubungi layanan AI: {exc}"[:300])
    return {"accepted": True}


# ---------- tabel data ----------

def _saring(media, label, q):
    kondisi, params = [], {}
    if media:
        kondisi.append("media = %(media)s")
        params["media"] = media
    if label:
        if label == "empty":
            kondisi.append("status = 'empty'")
        elif label in LABEL:
            kondisi.append("label = %(label)s")
            params["label"] = label
        else:
            raise HTTPException(400, "Sentimen harus positive, neutral, negative, atau empty.")
    if q:
        kondisi.append("(text ilike %(q)s or clean_text ilike %(q)s)")
        params["q"] = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    return ("where " + " and ".join(kondisi)) if kondisi else "", params


@app.get("/api/responses", dependencies=[Depends(get_current_user)])
def tabel(
    media: str = "", label: str = "", q: str = Query("", max_length=100),
    halaman: int = Query(1, ge=1), per_halaman: int = Query(25, ge=5, le=100),
):
    where, params = _saring(media.strip(), label.strip(), q.strip())
    with konek() as conn:
        total = conn.execute(f"select count(*) as n from responses {where}", params).fetchone()["n"]
        baris = conn.execute(
            "select id, media, text, clean_text, label, confidence, status from responses "
            f"{where} order by id limit %(lim)s offset %(off)s",
            {**params, "lim": per_halaman, "off": (halaman - 1) * per_halaman},
        ).fetchall()
    return {"total": total, "halaman": halaman, "per_halaman": per_halaman, "baris": baris}


@app.get("/api/responses/export", dependencies=[Depends(get_current_user)])
def ekspor(media: str = "", label: str = "", q: str = Query("", max_length=100)):
    where, params = _saring(media.strip(), label.strip(), q.strip())
    with konek() as conn:
        baris = conn.execute(
            "select media, text, clean_text, label, confidence from responses "
            f"{where} order by id limit 20000",
            params,
        ).fetchall()
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["media", "teks_awal", "teks_preprocessing", "sentimen", "confidence"])
    for b in baris:
        w.writerow([b["media"], b["text"], b["clean_text"] or "", b["label"] or "", "" if b["confidence"] is None else round(b["confidence"], 4)])
    return Response(
        "\ufeff" + out.getvalue(), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="tanggapan.csv"'},
    )


# ---------- interpretasi ----------

@app.get("/api/media/{media}/interpretation", dependencies=[Depends(get_current_user)])
def interpretasi(media: str):
    with konek() as conn:
        tandai_macet(conn)
        t = conn.execute("select id from interpretations where media=%s order by id desc limit 1", (media,)).fetchone()
        s = conn.execute(
            "select id from interpretations where media=%s and status='done' order by id desc limit 1", (media,)
        ).fetchone()
        jumlah = conn.execute(
            "select count(*) filter (where status='ok') as total, count(*) filter (where status='pending') as pending "
            "from responses where media=%s",
            (media,),
        ).fetchone()
        return {
            "terbaru": muat_interpretasi(conn, t["id"]) if t else None,
            "terakhir_selesai": muat_interpretasi(conn, s["id"]) if s else None,
            "jumlah_teks": jumlah["total"],
            "menunggu_prediksi": jumlah["pending"],
        }


def kirim_interpretasi(conn, interpretation_id):
    try:
        panggil_space("/jobs/interpret", {"interpretation_id": interpretation_id})
    except Exception as exc:
        conn.execute(
            "update interpretations set status='failed', error=%s, updated_at=now() where id=%s",
            (f"Gagal menghubungi layanan AI: {exc}"[:500], interpretation_id),
        )


@app.post("/api/media/{media}/interpret", status_code=202)
def jalankan_interpretasi(media: str, user: dict = Depends(get_current_user)):
    with konek() as conn:
        tandai_macet(conn)
        jumlah = conn.execute(
            "select count(*) filter (where status='ok') as total, count(*) filter (where status='pending') as pending "
            "from responses where media=%s",
            (media,),
        ).fetchone()
        if jumlah["total"] == 0:
            raise HTTPException(400, "Belum ada tanggapan berlabel pada media ini.")
        if jumlah["pending"] > 0:
            raise HTTPException(409, "Prediksi sentimen untuk data impor masih berjalan. Tunggu sampai selesai.")
        aktif = conn.execute(
            "select id from interpretations where media=%s and status in ('queued','running')", (media,)
        ).fetchone()
        if aktif:
            raise HTTPException(409, "Interpretasi untuk media ini sedang diproses.")
        run = conn.execute(
            "insert into interpretations (user_id, media) values (%s, %s) returning id",
            (user["id"], media),
        ).fetchone()
        with conn.cursor() as cur:
            cur.executemany(
                "insert into interpretation_results (interpretation_id, stage) values (%s, %s)", [(run["id"], t) for t in TAHAP]
            )
        kirim_interpretasi(conn, run["id"])
        return muat_interpretasi(conn, run["id"])


@app.post("/api/interpretations/{interpretation_id}/retry", dependencies=[Depends(get_current_user)], status_code=202)
def ulangi_interpretasi(interpretation_id: int):
    with konek() as conn:
        run = conn.execute("select media, status from interpretations where id=%s", (interpretation_id,)).fetchone()
        if run is None:
            raise HTTPException(404, "Pekerjaan tidak ditemukan.")
        if run["status"] != "failed":
            raise HTTPException(409, "Hanya pekerjaan yang gagal yang bisa diulang.")
        aktif = conn.execute(
            "select id from interpretations where media=%s and status in ('queued','running')", (run["media"],)
        ).fetchone()
        if aktif:
            raise HTTPException(409, "Interpretasi untuk media ini sedang diproses.")
        conn.execute(
            "update interpretation_results set status='waiting', error=null where interpretation_id=%s and status in ('failed','running')",
            (interpretation_id,),
        )
        conn.execute("update interpretations set status='queued', error=null, updated_at=now() where id=%s", (interpretation_id,))
        kirim_interpretasi(conn, interpretation_id)
        return muat_interpretasi(conn, interpretation_id)
