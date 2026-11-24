"""Layanan AI Arisza (FastAPI): preprocessing, Hybrid IndoBERT-BiLSTM, dan Llama 3.2 3B Instruct."""
import hmac
import logging
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import config, tasks
from .interpret import METODE, run_interpretation
from .jobs import JobStore
from .llama_service import LlamaService
from .lazy_hybrid import LazyHybridService

# Hanya tampilkan log INFO dari layanan Arisza agar tab Logs di Space tidak dipenuhi
# log internal pustaka (seperti pengecekan berkas opsional oleh httpx2/huggingface_hub).
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
_log_arisza = logging.getLogger("arisza")
_log_arisza.setLevel(logging.INFO)
if not _log_arisza.handlers:
    _log_arisza.addHandler(_handler)
_log_arisza.propagate = False
for _nama in ("httpx", "httpx2", "httpcore", "matplotlib", "huggingface_hub", "urllib3"):
    logging.getLogger(_nama).setLevel(logging.WARNING)


class PredictRequest(BaseModel):
    texts: list[str] = Field(min_length=1)


class InterpretItem(BaseModel):
    text: str = Field(min_length=1, description="Teks tanggapan asli, bukan hasil preprocessing.")
    label: Literal["negative", "neutral", "positive"]
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class InterpretRequest(BaseModel):
    media: str = Field(min_length=1, max_length=100)
    items: list[InterpretItem] = Field(min_length=1, max_length=5000)


class BatchRequest(BaseModel):
    batch_id: int


class InterpretationRequest(BaseModel):
    interpretation_id: int


class LengkapiRequest(BaseModel):
    media: Optional[str] = None


class WordcloudRequest(BaseModel):
    media: str = Field(min_length=1, max_length=100)


def periksa_kunci(x_api_key: str = Header(default="")):
    if not config.API_KEY:
        raise HTTPException(status_code=503, detail="API_KEY belum diatur pada Space.")
    if not hmac.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(status_code=401, detail="Kunci API tidak valid.")


def create_app(hybrid=None, llama=None):
    @asynccontextmanager
    async def lifespan(app):
        # Jangan unduh/muat bobot Hybrid saat startup. FastAPI harus tetap dapat
        # menerima /health meskipun unduhan model memerlukan waktu atau gagal.
        app.state.hybrid = hybrid if hybrid is not None else LazyHybridService()
        app.state.llama = llama if llama is not None else LlamaService(
            config.LLAMA_MODEL_ID, config.HF_TOKEN, config.LLAMA_DTYPE
        )
        app.state.jobs = JobStore(config.MAX_JOBS_KEPT)        # Llama (satu pekerjaan pada satu waktu)
        app.state.jobs_data = JobStore(config.MAX_JOBS_KEPT)   # prediksi sentimen dan Word Cloud
        yield
        app.state.jobs.shutdown()
        app.state.jobs_data.shutdown()

    app = FastAPI(title="Arisza AI Service", lifespan=lifespan)

    # HEAD juga diterima (include_in_schema=False agar tidak muncul Duplicate Operation ID).
    @app.get("/")
    @app.head("/", include_in_schema=False)
    def root():
        return {"service": "Arisza AI Service", "docs": "/docs", "health": "/health"}

    @app.get("/health")
    @app.head("/health", include_in_schema=False)
    def health():
        llama = app.state.llama
        hybrid_service = app.state.hybrid
        hybrid_loaded = getattr(hybrid_service, "loaded", True)
        hybrid_error = getattr(hybrid_service, "load_error", None)
        return {
            "status": "ok",
            "api_key_configured": bool(config.API_KEY),
            "database_configured": bool(config.DATABASE_URL),
            "hf_token_configured": bool(config.HF_TOKEN),
            "hybrid_loaded": hybrid_loaded,
            "hybrid_status": "loaded" if hybrid_loaded else ("load_failed" if hybrid_error else "not_loaded"),
            "hybrid_load_error": hybrid_error,
            "llama_model": llama.model_id,
            "llama_loaded": llama.loaded,
            "llama_load_seconds": llama.load_seconds,
            "interpretation_method": METODE,
            "max_input_tokens": config.LLAMA_MAX_INPUT_TOKENS,
            "max_new_pola": config.LLAMA_MAX_NEW_POLA,
            "max_new_saran": config.LLAMA_MAX_NEW_SARAN,
        }

    @app.post("/predict", dependencies=[Depends(periksa_kunci)])
    def predict(req: PredictRequest):
        if len(req.texts) > config.MAX_PREDICT_TEXTS:
            raise HTTPException(
                status_code=413,
                detail=f"Maksimal {config.MAX_PREDICT_TEXTS} teks per permintaan; kirim secara bertahap.",
            )
        hasil = app.state.hybrid.predict(req.texts, batch_size=config.PREDICT_BATCH_SIZE)
        return {"count": len(hasil), "results": hasil}

    @app.post("/interpret", status_code=202, dependencies=[Depends(periksa_kunci)])
    def interpret(req: InterpretRequest):
        items = [i.model_dump() for i in req.items]
        llama = app.state.llama

        def kerjakan():
            return run_interpretation(
                req.media, items, config.LLAMA_MAX_INPUT_TOKENS,
                config.LLAMA_MAX_NEW_POLA, config.LLAMA_MAX_NEW_SARAN,
                llama.generate, count_input_tokens_fn=llama.count_input_tokens,
                model_id=llama.model_id,
            )

        job_id = app.state.jobs.submit(kerjakan)
        return {"job_id": job_id, "status": "queued"}

    @app.get("/jobs/{job_id}", dependencies=[Depends(periksa_kunci)])
    def job_status(job_id: str):
        job = app.state.jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Pekerjaan tidak ditemukan (mungkin Space sempat restart).")
        return job

    # ---- Alur sistem web: Space membaca dan menulis langsung ke PostgreSQL ----
    def _perlu_db():
        if not config.DATABASE_URL:
            raise HTTPException(status_code=503, detail="DATABASE_URL belum diatur pada Space.")

    @app.post("/jobs/classify", status_code=202, dependencies=[Depends(periksa_kunci)])
    def job_klasifikasi(req: BatchRequest):
        _perlu_db()
        app.state.jobs_data.submit(
            lambda: tasks.klasifikasi_batch(req.batch_id, app.state.hybrid), kunci=f"classify:{req.batch_id}"
        )
        return {"accepted": True, "batch_id": req.batch_id}

    @app.post("/jobs/interpret", status_code=202, dependencies=[Depends(periksa_kunci)])
    def job_interpretasi(req: InterpretationRequest):
        _perlu_db()
        app.state.jobs.submit(
            lambda: tasks.proses_interpretasi(req.interpretation_id, app.state.llama), kunci=f"interpretation:{req.interpretation_id}"
        )
        return {"accepted": True, "interpretation_id": req.interpretation_id}

    @app.post("/jobs/complete", status_code=202, dependencies=[Depends(periksa_kunci)])
    def job_lengkapi(req: LengkapiRequest):
        """Isi teks hasil preprocessing dan Word Cloud untuk data lama (label tidak diubah)."""
        _perlu_db()
        app.state.jobs_data.submit(
            lambda: tasks.lengkapi_teks(app.state.hybrid, req.media), kunci=f"complete:{req.media or '*'}"
        )
        return {"accepted": True}

    @app.post("/jobs/wordcloud", status_code=202, dependencies=[Depends(periksa_kunci)])
    def job_wordcloud(req: WordcloudRequest):
        _perlu_db()
        app.state.jobs_data.submit(lambda: tasks.buat_wordcloud(req.media), kunci=f"wc:{req.media}")
        return {"accepted": True, "media": req.media}

    return app


app = create_app()
