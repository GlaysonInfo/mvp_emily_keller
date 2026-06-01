"""Trilha de auditoria — registra QUEM alterou O QUÊ e QUANDO.

Eventos são gravados no DynamoDB (tabela em AUDIT_LOG_TABLE) e, na ausência
dela ou em caso de falha, em um arquivo JSONL local (AUDIT_LOG_FILE, padrão
logs/audit.log). O registro NUNCA levanta exceção — auditoria não pode
derrubar a aplicação.

O "ator" (usuário logado) é guardado por sessão do Streamlit. O app define
isso uma vez por execução com set_actor(identity); os pontos de gravação
chamam record(...).

Esquema do item no DynamoDB:
    pk = TENANT#<tenant_id>
    sk = <iso_ts>#<event_id>
    + ts, event_id, action, user_email, role, tenant_id, target, details, source
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

try:  # streamlit é opcional (auditoria também funciona fora da IHM)
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

_ACTOR_KEY = "_audit_actor"


def set_actor(identity: Any) -> None:
    """Guarda o ator (usuário) na sessão atual, a partir da Identity."""
    if st is None or identity is None:
        return
    try:
        st.session_state[_ACTOR_KEY] = {
            "email": getattr(identity, "email", None),
            "role": getattr(identity, "role", None),
            "tenant_id": getattr(identity, "tenant_id", None),
        }
    except Exception:
        pass


def _current_actor() -> dict[str, Any]:
    if st is not None:
        try:
            actor = st.session_state.get(_ACTOR_KEY)
            if isinstance(actor, dict):
                return actor
        except Exception:
            pass
    return {}


def record(
    action: str,
    *,
    target: str | None = None,
    details: Any = None,
    tenant_id: str | None = None,
    status: str = "ok",
    actor: dict[str, Any] | None = None,
) -> None:
    """Registra um evento de auditoria. Silencioso em qualquer falha."""
    try:
        actor = actor or _current_actor()
        event = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event_id": uuid.uuid4().hex[:12],
            "action": str(action),
            "user_email": actor.get("email") or "anon",
            "role": actor.get("role"),
            "tenant_id": tenant_id or actor.get("tenant_id") or "-",
            "target": target,
            "details": details,
            "status": status,
            "source": "dashboard",
        }
        _persist(event)
    except Exception:
        pass


def _persist(event: dict[str, Any]) -> None:
    table = os.getenv("AUDIT_LOG_TABLE")
    if table:
        try:
            _persist_dynamo(table, event)
            return
        except Exception:
            pass  # cai para o arquivo
    _persist_file(event)


def _persist_dynamo(table: str, event: dict[str, Any]) -> None:
    import boto3

    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    profile = os.getenv("AWS_PROFILE") or None
    session = boto3.Session(profile_name=profile, region_name=region) if profile else boto3.Session(region_name=region)
    resource = session.resource("dynamodb")

    item = {k: v for k, v in event.items() if v is not None}
    item["pk"] = f"TENANT#{event['tenant_id']}"
    item["sk"] = f"{event['ts']}#{event['event_id']}"
    if isinstance(item.get("details"), (dict, list)):
        item["details"] = json.dumps(item["details"], ensure_ascii=False)
    resource.Table(table).put_item(Item=item)


def _persist_file(event: dict[str, Any]) -> None:
    path = os.getenv("AUDIT_LOG_FILE", "logs/audit.log")
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
