from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .grease_ingest_models import GreaseHealthResponse, GreaseIngestPayload, GreaseIngestResponse
from .grease_ingest_service import ensure_region, process_grease_ingest
from .grease_security_middleware import validate_grease_ingest_security
from .http_config import cors_origins_from_env

app = FastAPI(
    title="Grease Lubrication Ingest API",
    description="Endpoint HTTP para ingestão de ciclos de lubrificação por pressão.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_from_env("GREASE_ALLOWED_ORIGINS") or cors_origins_from_env(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.get("/grease/health", response_model=GreaseHealthResponse)
def grease_health():
    region = ensure_region()
    return GreaseHealthResponse(
        ok=True,
        service="grease-ingest-api",
        region=region,
        state_table=os.getenv("GREASE_STATE_TABLE", "grease_lubrication_state"),
        cycles_table=os.getenv("GREASE_CYCLES_TABLE", "grease_lubrication_cycles"),
        alerts_table=os.getenv("CONDITION_ALERTS_TABLE", "condition_alerts"),
    )


@app.post("/grease/ingest", response_model=GreaseIngestResponse)
async def grease_ingest(
    payload: GreaseIngestPayload,
    _security_ok: bool = Depends(validate_grease_ingest_security),
):
    try:
        return process_grease_ingest(payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail={
            "message": "Falha ao processar ciclo de lubrificação.",
            "error": str(exc),
            "error_type": type(exc).__name__,
        }) from exc


@app.get("/")
def root():
    return {"ok": True, "service": "grease-ingest-api", "endpoints": ["/grease/health", "/grease/ingest"]}
