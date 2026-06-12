from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timezone
import html
import logging
import os
import threading
import time
from typing import Any
from uuid import uuid4

import boto3

from .contact_models import ContactSubmission


LOGGER = logging.getLogger(__name__)
_RATE_LOCK = threading.Lock()
_RATE_EVENTS: dict[str, deque[float]] = defaultdict(deque)


def region_from_env() -> str:
    return os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"


def destination_email_from_env() -> str:
    return os.getenv("CONTACT_TO_EMAIL", "suporte@meuprompt.net").strip()


def source_email_from_env() -> str:
    return os.getenv("CONTACT_FROM_EMAIL", "").strip()


def delivery_configured() -> bool:
    return bool(source_email_from_env() and destination_email_from_env())


def rate_limit_from_env() -> tuple[int, int]:
    limit = max(1, int(os.getenv("CONTACT_RATE_LIMIT", "5")))
    window_seconds = max(60, int(os.getenv("CONTACT_RATE_WINDOW_SECONDS", "900")))
    return limit, window_seconds


def check_rate_limit(client_key: str, now: float | None = None) -> bool:
    limit, window_seconds = rate_limit_from_env()
    current = time.monotonic() if now is None else now
    cutoff = current - window_seconds

    with _RATE_LOCK:
        events = _RATE_EVENTS[client_key]
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(current)
    return True


def reset_rate_limits() -> None:
    with _RATE_LOCK:
        _RATE_EVENTS.clear()


def _message_subject(payload: ContactSubmission) -> str:
    if payload.subject:
        return payload.subject.replace("\r", " ").replace("\n", " ")
    company = f" - {payload.company}" if payload.company else ""
    return f"{payload.contact_type} Sentinela Industrial{company}".replace("\r", " ").replace("\n", " ")


def _text_body(payload: ContactSubmission, request_id: str, client_ip: str) -> str:
    created_at = datetime.now(timezone.utc).isoformat()
    return "\n".join(
        [
            "Nova solicitação pelo site Sentinela Industrial",
            "",
            f"Tipo: {payload.contact_type}",
            f"Nome: {payload.name}",
            f"E-mail: {payload.email}",
            f"Empresa: {payload.company or 'Não informada'}",
            f"Telefone: {payload.phone or 'Não informado'}",
            "",
            "Mensagem:",
            payload.message,
            "",
            f"Consentimento LGPD: {'Sim' if payload.consent else 'Não'}",
            f"Data UTC: {created_at}",
            f"IP de origem: {client_ip}",
            f"ID da solicitação: {request_id}",
        ]
    )


def _html_body(payload: ContactSubmission, request_id: str) -> str:
    def safe(value: str) -> str:
        return html.escape(value).replace("\n", "<br>")

    return f"""
    <html>
      <body style="font-family:Arial,sans-serif;color:#0f172a;line-height:1.5">
        <h2>Nova solicitação pelo site Sentinela Industrial</h2>
        <p><strong>Tipo:</strong> {safe(payload.contact_type)}</p>
        <p><strong>Nome:</strong> {safe(payload.name)}</p>
        <p><strong>E-mail:</strong> {safe(payload.email)}</p>
        <p><strong>Empresa:</strong> {safe(payload.company or "Não informada")}</p>
        <p><strong>Telefone:</strong> {safe(payload.phone or "Não informado")}</p>
        <h3>Mensagem</h3>
        <p>{safe(payload.message)}</p>
        <hr>
        <p style="font-size:12px;color:#64748b">ID da solicitação: {safe(request_id)}</p>
      </body>
    </html>
    """.strip()


def send_contact_email(
    payload: ContactSubmission,
    *,
    client_ip: str,
    ses_client: Any | None = None,
) -> str:
    if not payload.consent:
        raise ValueError("O consentimento de privacidade é obrigatório.")
    if not delivery_configured():
        raise RuntimeError("O remetente do serviço de contato não foi configurado.")

    request_id = uuid4().hex
    client = ses_client or boto3.client("ses", region_name=region_from_env())
    response = client.send_email(
        Source=source_email_from_env(),
        Destination={"ToAddresses": [destination_email_from_env()]},
        ReplyToAddresses=[payload.email],
        Message={
            "Subject": {"Data": _message_subject(payload), "Charset": "UTF-8"},
            "Body": {
                "Text": {"Data": _text_body(payload, request_id, client_ip), "Charset": "UTF-8"},
                "Html": {"Data": _html_body(payload, request_id), "Charset": "UTF-8"},
            },
        },
    )
    LOGGER.info(
        "Contact request delivered request_id=%s ses_message_id=%s",
        request_id,
        response.get("MessageId", ""),
    )
    return request_id
