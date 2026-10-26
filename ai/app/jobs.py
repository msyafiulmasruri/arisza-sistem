"""Antrean pekerjaan sederhana (satu pekerja) di memori.

Cocok untuk Space uji. Bila Space restart, daftar pekerjaan hilang.
Pada sistem final, status dan hasil disimpan di basis data.
"""
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone


def _sekarang():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    def __init__(self, max_kept=50):
        self._jobs = {}
        self._order = []
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1)  # satu pekerjaan Llama pada satu waktu
        self._max_kept = max_kept

    def submit(self, fn):
        job_id = uuid.uuid4().hex[:12]
        job = {
            "job_id": job_id, "status": "queued", "created_at": _sekarang(),
            "started_at": None, "finished_at": None, "result": None, "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
            self._order.append(job_id)
            while len(self._order) > self._max_kept:
                self._jobs.pop(self._order.pop(0), None)

        def jalankan():
            job["status"] = "running"
            job["started_at"] = _sekarang()
            try:
                job["result"] = fn()
                job["status"] = "done"
            except Exception as exc:  # pesan galat disimpan agar bisa dilihat dari status
                job["error"] = f"{type(exc).__name__}: {exc}"
                job["status"] = "failed"
            finally:
                job["finished_at"] = _sekarang()

        self._executor.submit(jalankan)
        return job_id

    def get(self, job_id):
        with self._lock:
            return self._jobs.get(job_id)

    def shutdown(self):
        self._executor.shutdown(wait=False, cancel_futures=True)
