from __future__ import annotations

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .grease_ingest_models import GreaseHealthResponse, GreaseIngestPayload, GreaseIngestResponse
from .grease_ingest_service import ensure_region, process_grease_ingest

app = FastAPI(
    title="Grease Lubrication Ingest API",
    description="Endpoint HTTP para ingestão de ciclos de lubrificação por pressão.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def check_token(x_api_key: str | None, authorization: str | None) -> None:
    expected = os.getenv("GREASE_INGEST_TOKEN")
    if not expected:
        return
    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    if x_api_key == expected or bearer == expected:
        return
    raise HTTPException(status_code=401, detail="Token de ingestão inválido ou ausente.")


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
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
):
    check_token(x_api_key, authorization)
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
