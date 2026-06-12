from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .contact_models import ContactHealthResponse, ContactSubmission, ContactSubmissionResponse
from .contact_service import (
    check_rate_limit,
    delivery_configured,
    region_from_env,
    send_contact_email,
)
from .http_config import cors_origins_from_env


LOGGER = logging.getLogger(__name__)
DEFAULT_ORIGINS = [
    "https://sentinelaindustrial.com.br",
    "https://www.sentinelaindustrial.com.br",
]

app = FastAPI(
    title="Sentinela Industrial Contact API",
    description="Recepção segura de solicitações comerciais do site institucional.",
    version="1.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

allowed_origins = cors_origins_from_env("CONTACT_ALLOWED_ORIGINS") or DEFAULT_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _client_ip(request: Request) -> str:
    real_ip = request.headers.get("x-real-ip", "").strip()
    if real_ip:
        return real_ip[:64]
    return request.client.host if request.client else "unknown"


def _validate_origin(request: Request) -> None:
    origin = request.headers.get("origin", "").strip()
    if origin and origin not in allowed_origins:
        raise HTTPException(status_code=403, detail="Origem não autorizada.")


@app.get("/contact/health", response_model=ContactHealthResponse)
def contact_health() -> ContactHealthResponse:
    return ContactHealthResponse(
        ok=True,
        service="contact-api",
        region=region_from_env(),
        delivery_configured=delivery_configured(),
    )


@app.post("/contact/submit", response_model=ContactSubmissionResponse)
async def submit_contact(payload: ContactSubmission, request: Request) -> ContactSubmissionResponse:
    _validate_origin(request)
    client_ip = _client_ip(request)

    if payload.website:
        return ContactSubmissionResponse(
            ok=True,
            message="Solicitação recebida.",
            request_id="accepted",
        )
    if not payload.consent:
        raise HTTPException(status_code=422, detail="O consentimento de privacidade é obrigatório.")
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Limite de solicitações atingido. Aguarde alguns minutos ou use o WhatsApp.",
        )

    try:
        request_id = send_contact_email(payload, client_ip=client_ip)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        LOGGER.exception("Contact delivery failed client_ip=%s error_type=%s", client_ip, type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail="Não foi possível enviar a solicitação agora. Tente novamente ou use o WhatsApp.",
        ) from exc

    return ContactSubmissionResponse(
        ok=True,
        message="Solicitação enviada. Nossa equipe entrará em contato.",
        request_id=request_id,
    )


@app.get("/")
def root() -> dict[str, object]:
    return {
        "ok": True,
        "service": "contact-api",
        "endpoints": ["/contact/health", "/contact/submit"],
    }
