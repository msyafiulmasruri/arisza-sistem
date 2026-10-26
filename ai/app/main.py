"""Layanan AI Arisza (FastAPI): preprocessing, Hybrid IndoBERT-BiLSTM, dan Llama 3.2 3B Instruct."""
import hmac
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import config, tasks
from .interpret import run_interpretation
from .jobs import JobStore
from .llama_service import LlamaService


class PredictRequest(BaseModel):
    texts: list[str] = Field(min_length=1)


class InterpretItem(BaseModel):
    text: str = Field(min_length=1)
    label: Literal["negative", "neutral", "positive"]
    confidence: float = Field(ge=0.0, le=1.0)


class InterpretRequest(BaseModel):
    media: str = Field(min_length=1, max_length=100)
    items: list[InterpretItem] = Field(min_length=1, max_length=5000)
    top_k: Optional[int] = Field(default=None, ge=1, le=50)              # untuk uji coba nilai k
    max_new_tokens: Optional[int] = Field(default=None, ge=50, le=800)


class BatchRequest(BaseModel):
    batch_id: int


class RunRequest(BaseModel):
    run_id: int


def periksa_kunci(x_api_key: str = Header(default="")):
    if not config.API_KEY:
        raise HTTPException(status_code=503, detail="API_KEY belum diatur pada Space.")
    if not hmac.compare_digest(x_api_key, config.API_KEY):
        raise HTTPException(status_code=401, detail="Kunci API tidak valid.")


def _muat_hybrid():
    from .hybrid_model import HybridService  # dimuat di sini agar modul lain bisa diuji tanpa torch
    return HybridService(config.MODEL_DIR)


def create_app(hybrid=None, llama=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.hybrid = hybrid if hybrid is not None else _muat_hybrid()
        app.state.llama = llama if llama is not None else LlamaService(
            config.LLAMA_MODEL_ID, config.HF_TOKEN, config.LLAMA_DTYPE
        )
        app.state.jobs = JobStore(config.MAX_JOBS_KEPT)
        yield
        app.state.jobs.shutdown()

    app = FastAPI(title="Arisza AI Service", lifespan=lifespan)

    @app.get("/")
    def root():
        return {"service": "Arisza AI Service", "docs": "/docs", "health": "/health"}

    @app.get("/health")
    def health():
        llama = app.state.llama
        return {
            "status": "ok",
            "hybrid_loaded": app.state.hybrid is not None,
            "llama_model": llama.model_id,
            "llama_loaded": llama.loaded,
            "llama_load_seconds": llama.load_seconds,
            "top_k_default": config.LLAMA_TOP_K,
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
        k = req.top_k or config.LLAMA_TOP_K
        max_new = req.max_new_tokens or config.LLAMA_MAX_NEW_TOKENS
        items = [i.model_dump() for i in req.items]
        llama = app.state.llama

        def kerjakan():
            return run_interpretation(
                req.media, items, k, max_new, config.MAX_TEXT_CHARS,
                llama.generate, model_id=llama.model_id,
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
        app.state.jobs.submit(lambda: tasks.klasifikasi_batch(req.batch_id, app.state.hybrid))
        return {"accepted": True, "batch_id": req.batch_id}

    @app.post("/jobs/interpret", status_code=202, dependencies=[Depends(periksa_kunci)])
    def job_interpretasi(req: RunRequest):
        _perlu_db()
        app.state.jobs.submit(lambda: tasks.interpretasi_run(req.run_id, app.state.llama))
        return {"accepted": True, "run_id": req.run_id}

    return app


app = create_app()
