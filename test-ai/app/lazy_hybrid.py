"""Pemuatan model Hybrid secara tertunda agar FastAPI tetap dapat startup."""
import logging
import threading

from . import config

log = logging.getLogger("arisza")


def _muat_hybrid():
    # Import torch dan transformers hanya ketika model benar-benar diperlukan.
    from .hybrid_model import HybridService
    return HybridService(config.MODEL_DIR)


class LazyHybridService:
    """Memuat bobot Hybrid saat klasifikasi pertama kali diminta.

    Kegagalan unduh atau pemuatan model tidak menggagalkan startup FastAPI.
    Permintaan berikutnya dapat mencoba memuat ulang setelah kegagalan sementara.
    """

    def __init__(self):
        self._service = None
        self._load_error = None
        self._lock = threading.Lock()

    @property
    def loaded(self):
        return self._service is not None

    @property
    def load_error(self):
        return self._load_error

    def _get_service(self):
        if self._service is not None:
            return self._service
        with self._lock:
            if self._service is not None:
                return self._service
            try:
                self._service = _muat_hybrid()
                self._load_error = None
                log.info("Model Hybrid berhasil dimuat.")
            except Exception as exc:
                self._load_error = f"{type(exc).__name__}: {exc}"[:500]
                log.exception("Model Hybrid gagal dimuat; layanan API tetap aktif.")
                raise RuntimeError(
                    "Model Hybrid gagal dimuat. Periksa akses repository model, "
                    "koneksi Hugging Face, dan kapasitas memori Space. Detail: "
                    f"{self._load_error}"
                ) from exc
        return self._service

    @property
    def slang_map(self):
        return self._get_service().slang_map

    def predict(self, texts, batch_size=16):
        return self._get_service().predict(texts, batch_size=batch_size)
