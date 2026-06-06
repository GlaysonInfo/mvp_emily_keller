from __future__ import annotations

from typing import Any


def current_actor_snapshot() -> dict[str, Any]:
    """Return the authenticated audit actor without exposing auth internals."""
    try:
        from dashboard.auth import audit
    except ImportError:  # pragma: no cover - supports streamlit run from repo root.
        try:
            from src.dashboard.auth import audit
        except ImportError:
            return {}

    return audit.current_actor()


def record_sensitive_action(
    action: str,
    *,
    target: str | None = None,
    details: Any = None,
    tenant_id: str | None = None,
    status: str = "ok",
) -> None:
    """Record a dashboard audit event without coupling pages to auth internals."""
    try:
        from dashboard.auth import audit
    except ImportError:  # pragma: no cover - supports streamlit run from repo root.
        try:
            from src.dashboard.auth import audit
        except ImportError:
            audit = None  # type: ignore[assignment]

    if audit is None:
        return

    audit.record(
        action,
        target=target,
        details=details,
        tenant_id=tenant_id,
        status=status,
    )
