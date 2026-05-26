from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .condition_ingest_models import ConditionHealthResponse, ConditionIngestPayload, ConditionIngestResponse
from .condition_ingest_service import (
    alerts_table_name_from_env,
    ensure_region,
    history_table_name_from_env,
    process_condition_ingest,
    state_table_name_from_env,
)
from .condition_security_middleware import validate_condition_ingest_security

app = FastAPI(
    title="Condition Monitoring Ingest API",
    description="Endpoint HTTP para ingestão de telemetria de condição de equipamentos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/condition/health", response_model=ConditionHealthResponse)
def condition_health():
    region = ensure_region()
    return ConditionHealthResponse(
        ok=True,
        service="condition-ingest-api",
        region=region,
        state_table=state_table_name_from_env(),
        history_table=history_table_name_from_env(),
        alerts_table=alerts_table_name_from_env(),
    )


@app.post("/condition/ingest", response_model=ConditionIngestResponse)
async def condition_ingest(
    payload: ConditionIngestPayload,
    _security_ok: bool = Depends(validate_condition_ingest_security),
):
    try:
        return process_condition_ingest(payload)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Falha ao processar telemetria de condição.",
                "error": str(exc),
                "error_type": type(exc).__name__,
            },
        ) from exc


@app.get("/")
def root():
    return {"ok": True, "service": "condition-ingest-api", "endpoints": ["/condition/health", "/condition/ingest"]}
