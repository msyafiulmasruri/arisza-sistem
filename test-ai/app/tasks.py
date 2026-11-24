"""Pekerjaan latar belakang yang membaca dan menulis langsung ke PostgreSQL.

Backend Vercel hanya mencatat permintaan (baris batch atau run) lalu memanggil Space.
Space mengerjakan sisanya dan memperbarui status di basis data pada setiap tahap.
"""
import logging
import threading
import time
from contextlib import contextmanager

from psycopg.types.json import Jsonb

from . import config, db, wordcloud_png, wordtext
from .interpret import (
    METODE, NAMA, URUTAN, TIDAK_ADA_POLA, TIDAK_ADA_TANGGAPAN,
    bersihkan_saran, buat_catatan, buat_detail_kosong, buat_pesan_saran, interpretasi_sentimen,
)
from .preprocessing import preprocess

log = logging.getLogger("arisza.tasks")

DETAK_DETIK = 60  # selang pembaruan updated_at selama pekerjaan berjalan


def _galat(exc):
    return f"{type(exc).__name__}: {exc}"[:500]


@contextmanager
def _detak(sql, params):
    """Perbarui updated_at secara berkala selama pekerjaan berjalan.

    Satu panggilan Llama di CPU bisa memakan waktu lama; tanpa detak ini backend dapat
    mengira pekerjaan macet (BATAS_MACET_MENIT) padahal Space masih bekerja.
    """
    berhenti = threading.Event()

    def ulang():
        while not berhenti.wait(DETAK_DETIK):
            try:
                db.jalankan(sql, params)
            except Exception:
                log.warning("Gagal memperbarui detak pekerjaan", exc_info=True)

    t = threading.Thread(target=ulang, daemon=True)
    t.start()
    try:
        yield
    finally:
        berhenti.set()


# ---------- Word Cloud ----------

def buat_wordcloud(media):
    """Buat ulang gambar Word Cloud tiap sentimen untuk satu media dan simpan di basis data."""
    baris = db.ambil(
        "select label, wc_text from responses where media=%s and status='ok' and wc_text is not null and wc_text<>''",
        (media,),
    )
    per = {l: [] for l in URUTAN}
    for b in baris:
        per[b["label"]].append(b["wc_text"])
    for label in URUTAN:
        if not per[label]:
            db.jalankan("delete from wordclouds where media=%s and label=%s", (media, label))
            continue
        try:
            png = wordcloud_png.buat(" ".join(per[label]), label)
        except ValueError:  # mis. tidak ada kata yang bisa digambar; sentimen lain tetap diproses
            log.warning("Word Cloud %s/%s dilewati: tidak ada kata yang bisa digambar", media, label)
            continue
        db.jalankan(
            "insert into wordclouds (media, label, image, n_texts, updated_at) values (%s,%s,%s,%s,now()) "
            "on conflict (media, label) do update set image=excluded.image, n_texts=excluded.n_texts, updated_at=now()",
            (media, label, png, len(per[label])),
        )


def _wordcloud_aman(daftar_media):
    for m in daftar_media:
        try:
            buat_wordcloud(m)
        except Exception:  # kegagalan Word Cloud tidak boleh menggagalkan prediksi
            log.exception("Word Cloud gagal untuk media %s", m)


# ---------- prediksi sentimen saat impor ----------

def klasifikasi_batch(batch_id, hybrid, ukuran=64):
    try:
        log.info("Klasifikasi batch %s dimulai", batch_id)
        t0 = time.perf_counter()
        db.jalankan("update batches set status='running', error=null, updated_at=now() where id=%s", (batch_id,))
        diproses = 0
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
                    data.append((h["sentiment"], h["confidence"], "ok", h["clean_text"], wordtext.buat(h["clean_text"]), b["id"]))
                else:
                    data.append((None, None, "empty", "", "", b["id"]))
            db.banyak(
                "update responses set label=%s, confidence=%s, status=%s, clean_text=%s, wc_text=%s where id=%s", data
            )
            db.jalankan("update batches set updated_at=now() where id=%s", (batch_id,))
            diproses += len(data)
        media = [r["media"] for r in db.ambil("select distinct media from responses where batch_id=%s", (batch_id,))]
        _wordcloud_aman(media)
        db.jalankan("update batches set status='done', updated_at=now() where id=%s", (batch_id,))
        log.info("Klasifikasi batch %s selesai: %s teks dalam %.1f detik", batch_id, diproses, time.perf_counter() - t0)
    except Exception as exc:
        log.exception("Klasifikasi batch %s gagal", batch_id)
        try:
            db.jalankan(
                "update batches set status='failed', error=%s, updated_at=now() where id=%s",
                (_galat(exc), batch_id),
            )
        except Exception:
            log.exception("Status gagal batch %s tidak dapat disimpan", batch_id)


# ---------- melengkapi data lama (tanpa memprediksi ulang) ----------

def lengkapi_teks(hybrid, media=None, ukuran=200):
    """Isi clean_text dan wc_text untuk baris lama yang sudah berlabel. Label tidak diubah."""
    kondisi, params = "status='ok' and (clean_text is null or wc_text is null)", ()
    if media:
        kondisi, params = kondisi + " and media=%s", (media,)
    diperbarui = 0
    while True:
        baris = db.ambil(f"select id, text from responses where {kondisi} order by id limit {int(ukuran)}", params)
        if not baris:
            break
        data = []
        for b in baris:
            bersih = preprocess(b["text"], hybrid.slang_map)
            data.append((bersih, wordtext.buat(bersih) if bersih else "", b["id"]))
        db.banyak("update responses set clean_text=%s, wc_text=%s where id=%s", data)
        diperbarui += len(data)
    daftar = [media] if media else [r["media"] for r in db.ambil("select distinct media from responses where status='ok'")]
    _wordcloud_aman(daftar)
    return {"diperbarui": diperbarui}


# ---------- interpretasi Llama per sentimen ----------

def _mulai(interpretation_id, tahap):
    db.jalankan(
        "update interpretation_results set status='running', error=null, started_at=now(), "
        "finished_at=null, detail=null where interpretation_id=%s and stage=%s",
        (interpretation_id, tahap),
    )
    db.jalankan("update interpretations set updated_at=now() where id=%s", (interpretation_id,))


def _selesai(interpretation_id, tahap, hasil, dipakai, total, durasi, detail=None):
    db.jalankan(
        "update interpretation_results set status='done', result=%s, texts_used=%s, texts_total=%s, "
        "duration=%s, detail=%s, finished_at=now() "
        "where interpretation_id=%s and stage=%s",
        (hasil, dipakai, total, durasi, Jsonb(detail) if detail is not None else None, interpretation_id, tahap),
    )
    db.jalankan("update interpretations set updated_at=now() where id=%s", (interpretation_id,))


def _gagal(interpretation_id, tahap, exc):
    pesan = _galat(exc)
    if tahap:
        db.jalankan(
            "update interpretation_results set status='failed', error=%s, finished_at=now() where interpretation_id=%s and stage=%s",
            (pesan, interpretation_id, tahap),
        )
    db.jalankan(
        "update interpretations set status='failed', error=%s, updated_at=now() where id=%s",
        (pesan, interpretation_id),
    )


def proses_interpretasi(interpretation_id, llama):
    """Interpretasikan teks tanggapan asli per media dan kategori sentimen."""
    tahap_sekarang = None
    try:
        run = db.ambil_satu("select * from interpretations where id=%s", (interpretation_id,))
        if run is None:
            log.warning("Run interpretasi %s tidak ditemukan di basis data", interpretation_id)
            return
        media = run["media"]
        log.info("Interpretasi run %s (media %s) dimulai dengan metode %s", interpretation_id, media, METODE)
        mulai_run = time.perf_counter()

        with _detak("update interpretations set updated_at=now() where id=%s and status in ('queued','running')",
                    (interpretation_id,)):
            # Gunakan teks tanggapan asli, bukan clean_text hasil preprocessing.
            baris = db.ambil(
                "select text, label from responses where media=%s and status='ok' "
                "and text is not null and btrim(text)<>'' "
                "and label in ('positive','neutral','negative') order by id",
                (media,),
            )
            if not baris:
                raise ValueError("Belum ada tanggapan berlabel pada media ini.")

            kelompok = {label: [] for label in URUTAN}
            for item in baris:
                teks = item["text"]
                if isinstance(teks, str) and teks.strip():
                    kelompok[item["label"]].append(teks)
            jumlah = {label: len(kelompok[label]) for label in URUTAN}
            total = sum(jumlah.values())
            if total == 0:
                raise ValueError("Tidak ada teks tanggapan asli yang dapat diinterpretasikan.")

            db.jalankan(
                "update interpretations set status='running', error=null, started_at=coalesce(started_at, now()), "
                "n_texts=%s, max_input_tokens=%s, max_new_pola=%s, max_new_saran=%s, "
                "updated_at=now() where id=%s",
                (total, config.LLAMA_MAX_INPUT_TOKENS, config.LLAMA_MAX_NEW_POLA,
                 config.LLAMA_MAX_NEW_SARAN, interpretation_id),
            )
            tahap = {
                t["stage"]: t
                for t in db.ambil(
                    "select * from interpretation_results where interpretation_id=%s", (interpretation_id,)
                )
            }
            hilang = [label for label in URUTAN + ["saran"] if label not in tahap]
            if hilang:
                raise ValueError(f"Baris tahap interpretasi tidak lengkap (tidak ada: {', '.join(hilang)}).")

            llama_siap = False

            def pastikan_llama_siap():
                nonlocal llama_siap
                if not llama_siap and hasattr(llama, "ensure_loaded"):
                    llama.ensure_loaded()
                llama_siap = True

            pola, detail_label = {}, {}
            for label in URUTAN:
                tahap_lama = tahap[label]
                detail_lama = tahap_lama["detail"] or {}
                if (
                    tahap_lama["status"] == "done"
                    and detail_lama.get("metode") == METODE
                    and detail_lama.get("jumlah_tanggapan") == jumlah[label]
                    and detail_lama.get("batas_masukan_token") == config.LLAMA_MAX_INPUT_TOKENS
                ):
                    pola[label] = tahap_lama["result"]
                    detail_label[label] = detail_lama
                    continue

                tahap_sekarang = label
                _mulai(interpretation_id, label)
                if jumlah[label] == 0:
                    hasil = TIDAK_ADA_TANGGAPAN.format(nama=NAMA[label])
                    detail = buat_detail_kosong(0, config.LLAMA_MAX_INPUT_TOKENS)
                    _selesai(interpretation_id, label, hasil, 0, 0, 0.0, detail)
                    pola[label], detail_label[label] = hasil, detail
                    continue

                pastikan_llama_siap()
                log.info(
                    "Run %s tahap %s: %s tanggapan asli, batas masukan %s token",
                    interpretation_id, label, jumlah[label], config.LLAMA_MAX_INPUT_TOKENS,
                )
                t0 = time.perf_counter()
                hasil, detail = interpretasi_sentimen(
                    media, label, kelompok[label], llama.generate, llama.count_input_tokens,
                    config.LLAMA_MAX_INPUT_TOKENS, config.LLAMA_MAX_NEW_POLA,
                )
                durasi_tahap = round(time.perf_counter() - t0, 2)
                _selesai(
                    interpretation_id, label, hasil, jumlah[label], jumlah[label], durasi_tahap, detail
                )
                log.info(
                    "Run %s tahap %s selesai: %s batch, %s panggilan Llama dalam %.1f detik",
                    interpretation_id, label, detail["jumlah_batch"], detail["panggilan_llama"], durasi_tahap,
                )
                pola[label], detail_label[label] = hasil, detail

            # Saran disusun setelah pola opini dari seluruh kategori tersedia.
            pola_tersedia = {label: pola[label] for label in URUTAN if jumlah[label] > 0}
            tahap_saran_lama = tahap["saran"]
            detail_saran_lama = tahap_saran_lama["detail"] or {}
            perlu_saran_baru = (
                tahap_saran_lama["status"] != "done"
                or detail_saran_lama.get("metode") != METODE
                or detail_saran_lama.get("jumlah_per_sentimen") != jumlah
                or detail_saran_lama.get("batas_masukan_token") != config.LLAMA_MAX_INPUT_TOKENS
            )

            if perlu_saran_baru:
                tahap_sekarang = "saran"
                _mulai(interpretation_id, "saran")
                if not pola_tersedia:
                    saran = TIDAK_ADA_POLA
                    detail_saran = {
                        "metode": METODE,
                        "llama_dipanggil": False,
                        "panggilan_llama": 0,
                        "jumlah_pola_digunakan": 0,
                        "jumlah_per_sentimen": dict(jumlah),
                        "batas_masukan_token": config.LLAMA_MAX_INPUT_TOKENS,
                    }
                    _selesai(interpretation_id, "saran", saran, None, None, 0.0, detail_saran)
                else:
                    pastikan_llama_siap()
                    pesan_saran = buat_pesan_saran(media, pola_tersedia, jumlah)
                    if llama.count_input_tokens(pesan_saran) > config.LLAMA_MAX_INPUT_TOKENS:
                        raise ValueError("Masukan penyusunan saran melebihi batas token masukan Llama.")
                    log.info("Run %s tahap saran: menyusun tiga saran tindak lanjut", interpretation_id)
                    t0 = time.perf_counter()
                    saran = bersihkan_saran(
                        llama.generate(pesan_saran, config.LLAMA_MAX_NEW_SARAN)
                    )
                    if not saran:
                        raise RuntimeError("Llama tidak menghasilkan saran tindak lanjut.")
                    durasi_saran = round(time.perf_counter() - t0, 2)
                    detail_saran = {
                        "metode": METODE,
                        "llama_dipanggil": True,
                        "panggilan_llama": 1,
                        "jumlah_pola_digunakan": len(pola_tersedia),
                        "jumlah_per_sentimen": dict(jumlah),
                        "batas_masukan_token": config.LLAMA_MAX_INPUT_TOKENS,
                    }
                    _selesai(interpretation_id, "saran", saran, None, None, durasi_saran, detail_saran)
                    log.info("Run %s tahap saran selesai dalam %.1f detik", interpretation_id, durasi_saran)
            else:
                saran = tahap_saran_lama["result"]
                detail_saran = detail_saran_lama

            jumlah_panggilan = sum(
                int(detail_label[label].get("panggilan_llama", 0)) for label in URUTAN
            ) + int(detail_saran.get("panggilan_llama", 0))
            jumlah_batch = sum(int(detail_label[label].get("jumlah_batch", 0)) for label in URUTAN)
            db.jalankan(
                "update interpretations set status='done', catatan=%s, finished_at=now(), updated_at=now() where id=%s",
                (buat_catatan(jumlah, total, jumlah_batch, jumlah_panggilan), interpretation_id),
            )
        log.info("Run interpretasi %s selesai dalam %.1f detik", interpretation_id, time.perf_counter() - mulai_run)
    except Exception as exc:
        log.exception("Run interpretasi %s gagal pada tahap %s", interpretation_id, tahap_sekarang)
        try:
            _gagal(interpretation_id, tahap_sekarang, exc)
        except Exception:
            log.exception("Status gagal run %s tidak dapat disimpan", interpretation_id)
