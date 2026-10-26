"""Pekerjaan latar belakang yang membaca dan menulis langsung ke PostgreSQL.

Backend Vercel hanya mencatat permintaan (baris batch atau run) lalu memanggil Space.
Space mengerjakan sisanya dan memperbarui status di basis data pada setiap tahap.
"""
import time

from . import config, db
from .interpret import NAMA, URUTAN, buat_catatan, buat_pesan_pola, buat_pesan_saran, pilih_teks


def _galat(exc):
    return f"{type(exc).__name__}: {exc}"[:500]


# ---------- prediksi sentimen saat impor ----------

def klasifikasi_batch(batch_id, hybrid, ukuran=64):
    try:
        db.jalankan("update import_batches set status='running', error=null, updated_at=now() where id=%s", (batch_id,))
        while True:
            baris = db.ambil(
                "select id, text from responses where batch_id=%s and status='pending' order by id limit %s",
                (batch_id, ukuran),
            )
            if not baris:
                break
            hasil = hybrid.predict([b["text"] for b in baris], batch_size=config.PREDICT_BATCH_SIZE)
            data = []
            for b, h in zip(baris, hasil):
                if h["status"] == "ok":
                    data.append((h["sentiment"], h["confidence"], "ok", b["id"]))
                else:
                    data.append((None, None, "empty", b["id"]))
            db.banyak("update responses set label=%s, confidence=%s, status=%s where id=%s", data)
            db.jalankan("update import_batches set updated_at=now() where id=%s", (batch_id,))
        db.jalankan("update import_batches set status='done', updated_at=now() where id=%s", (batch_id,))
    except Exception as exc:
        try:
            db.jalankan(
                "update import_batches set status='failed', error=%s, updated_at=now() where id=%s",
                (_galat(exc), batch_id),
            )
        except Exception:
            pass


# ---------- interpretasi Llama, bertahap ----------

def _mulai(run_id, tahap):
    db.jalankan(
        "update interpretation_stages set status='running', error=null, started_at=now() where run_id=%s and stage=%s",
        (run_id, tahap),
    )
    db.jalankan("update interpretation_runs set updated_at=now() where id=%s", (run_id,))


def _selesai(run_id, tahap, hasil, dipakai, total, durasi):
    db.jalankan(
        "update interpretation_stages set status='done', result=%s, texts_used=%s, texts_total=%s, "
        "duration=%s, finished_at=now() where run_id=%s and stage=%s",
        (hasil, dipakai, total, durasi, run_id, tahap),
    )
    db.jalankan("update interpretation_runs set updated_at=now() where id=%s", (run_id,))


def _gagal(run_id, tahap, exc):
    pesan = _galat(exc)
    if tahap:
        db.jalankan(
            "update interpretation_stages set status='failed', error=%s, finished_at=now() where run_id=%s and stage=%s",
            (pesan, run_id, tahap),
        )
    db.jalankan(
        "update interpretation_runs set status='failed', error=%s, updated_at=now() where id=%s",
        (pesan, run_id),
    )


def interpretasi_run(run_id, llama):
    tahap_sekarang = None
    try:
        run = db.ambil_satu("select * from interpretation_runs where id=%s", (run_id,))
        if run is None:
            return
        media = run["media"]
        k = run["top_k"] or config.LLAMA_TOP_K
        max_baru = run["max_new_tokens"] or config.LLAMA_MAX_NEW_TOKENS

        baris = db.ambil(
            "select text, label, confidence from responses where media=%s and status='ok' order by id", (media,)
        )
        if not baris:
            raise ValueError("Belum ada tanggapan berlabel pada media ini.")
        kelompok = {l: [] for l in URUTAN}
        for i, b in enumerate(baris):
            kelompok[b["label"]].append((i, {"text": b["text"], "confidence": float(b["confidence"] or 0)}))
        jumlah = {l: len(kelompok[l]) for l in URUTAN}
        total = len(baris)

        db.jalankan(
            "update interpretation_runs set status='running', error=null, started_at=coalesce(started_at, now()), "
            "n_texts=%s, top_k=%s, max_new_tokens=%s, updated_at=now() where id=%s",
            (total, k, max_baru, run_id),
        )
        tahap = {t["stage"]: t for t in db.ambil("select * from interpretation_stages where run_id=%s", (run_id,))}

        pola, dipakai = {}, {}
        for label in URUTAN:
            if tahap[label]["status"] == "done":  # tahap yang sudah selesai tidak diulang
                pola[label] = tahap[label]["result"]
                dipakai[label] = tahap[label]["texts_used"] or 0
                continue
            tahap_sekarang = label
            _mulai(run_id, label)
            if jumlah[label] == 0:
                hasil, n, durasi = f"Tidak ada tanggapan {NAMA[label]} pada media ini.", 0, 0.0
            else:
                terpilih = pilih_teks(kelompok[label], k, config.MAX_TEXT_CHARS)
                n = len(terpilih)
                t0 = time.perf_counter()
                hasil = llama.generate(buat_pesan_pola(media, label, terpilih, jumlah[label]), max_baru).strip()
                durasi = round(time.perf_counter() - t0, 2)
            _selesai(run_id, label, hasil, n, jumlah[label], durasi)
            pola[label], dipakai[label] = hasil, n

        if tahap["saran"]["status"] != "done":
            tahap_sekarang = "saran"
            _mulai(run_id, "saran")
            t0 = time.perf_counter()
            saran = llama.generate(buat_pesan_saran(media, pola, jumlah), max_baru).strip()
            _selesai(run_id, "saran", saran, None, None, round(time.perf_counter() - t0, 2))

        db.jalankan(
            "update interpretation_runs set status='done', catatan=%s, finished_at=now(), updated_at=now() where id=%s",
            (buat_catatan(jumlah, dipakai, total), run_id),
        )
    except Exception as exc:
        try:
            _gagal(run_id, tahap_sekarang, exc)
        except Exception:
            pass
