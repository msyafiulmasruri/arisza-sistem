"""Antrean pekerjaan sederhana (satu pekerja) di memori.

Cocok untuk Space uji. Bila Space restart, daftar pekerjaan hilang.
Status dan hasil pekerjaan sistem web disimpan di basis data, bukan di sini.
"""
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

log = logging.getLogger("arisza.jobs")


def _sekarang():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    def __init__(self, max_kept=50):
        self._jobs = {}
        self._order = []
        self._kunci_aktif = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)  # satu pekerjaan pada satu waktu
        self._max_kept = max_kept

    def submit(self, fn, kunci=None):
        """Jalankan fn di latar belakang. Bila `kunci` yang sama masih antre/berjalan, pakai pekerjaan itu."""
        with self._lock:
            if kunci and kunci in self._kunci_aktif:
                return self._kunci_aktif[kunci]
            job_id = uuid.uuid4().hex[:12]
            job = {
                "job_id": job_id, "status": "queued", "created_at": _sekarang(),
                "started_at": None, "finished_at": None, "result": None, "error": None,
            }
            self._jobs[job_id] = job
            self._order.append(job_id)
            if kunci:
                self._kunci_aktif[kunci] = job_id
            while len(self._order) > self._max_kept:
                self._jobs.pop(self._order.pop(0), None)

        def jalankan():
            job["status"] = "running"
            job["started_at"] = _sekarang()
            try:
                job["result"] = fn()
                job["status"] = "done"
            except Exception as exc:  # pesan galat disimpan agar bisa dilihat dari status
                log.exception("Pekerjaan %s (%s) gagal", job_id, kunci or "-")
                job["error"] = f"{type(exc).__name__}: {exc}"
                job["status"] = "failed"
            finally:
                job["finished_at"] = _sekarang()
                if kunci:
                    with self._lock:
                        self._kunci_aktif.pop(kunci, None)

        self._executor.submit(jalankan)
        return job_id

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def shutdown(self):
        self._executor.shutdown(wait=False, cancel_futures=True)
