from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

try:
    from dashboard.alerts_repository import now_utc, severity_from_status_label
    from dashboard.dynamodb_repository import normalize_active_alert_item
    from dashboard.history_repository import build_history_item
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.alerts_repository import now_utc, severity_from_status_label
    from src.dashboard.dynamodb_repository import normalize_active_alert_item
    from src.dashboard.history_repository import build_history_item


_DATA_DIR = Path(__file__).resolve().parent
_STATES_PATH = _DATA_DIR / "demo_multiasset_states.json"
_STATES: list[dict[str, Any]] | None = None
_ALERTS: list[dict[str, Any]] = []


def _load_seed_states() -> list[dict[str, Any]]:
    with _STATES_PATH.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    states = raw if isinstance(raw, list) else []
    normalized: list[dict[str, Any]] = []
    for item in states:
        if isinstance(item, dict):
            normalized.append(_normalize_state(item))
    return normalized


def _state_store() -> list[dict[str, Any]]:
    global _STATES
    if _STATES is None:
        _STATES = _load_seed_states()
    return _STATES


def _normalize_state(item: dict[str, Any]) -> dict[str, Any]:
    state = copy.deepcopy(item)
    tenant_id = str(state.get("tenant_id") or "cliente_demo")
    asset_id = str(state.get("asset_id") or "motor_001")
    state.setdefault("plant_id", "lab_virtual")
    state.setdefault("pk", f"TENANT#{tenant_id}#ASSET#{asset_id}")
    state.setdefault("sk", "LATEST")
    state.setdefault("tenant_asset", f"{tenant_id}#{asset_id}")
    return state


class LocalDemoRepository:
    """File-seeded repository for local navigation without AWS credentials."""

    def list_current_states(self, tenant_id: str, plant_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(state)
            for state in _state_store()
            if str(state.get("tenant_id")) == tenant_id
            and str(state.get("plant_id")) == plant_id
            and str(state.get("sk", "LATEST")) == "LATEST"
        ]

    def get_latest_state(self, tenant_id: str, asset_id: str) -> dict[str, Any] | None:
        for state in _state_store():
            if str(state.get("tenant_id")) == tenant_id and str(state.get("asset_id")) == asset_id:
                return copy.deepcopy(state)
        return None

    def get_active_alerts(self, tenant_id: str, asset_id: str) -> list[dict[str, Any]]:
        tenant_asset = f"{tenant_id}#{asset_id}"
        return [
            copy.deepcopy(alert)
            for alert in _ALERTS
            if str(alert.get("tenant_asset") or "") == tenant_asset
            or (str(alert.get("tenant_id")) == tenant_id and str(alert.get("asset_id")) == asset_id)
        ]

    @staticmethod
    def tenant_asset(tenant_id: str, asset_id: str) -> str:
        return f"{tenant_id}#{asset_id}"

    @staticmethod
    def legacy_pk(tenant_id: str, asset_id: str) -> str:
        return f"TENANT#{tenant_id}#ASSET#{asset_id}"

    def list_alerts(
        self,
        tenant_id: str,
        plant_id: str | None = None,
        asset_id: str | None = None,
        status: str | None = None,
        *,
        active_only: bool = False,
    ) -> list[dict[str, Any]]:
        alerts = [
            copy.deepcopy(alert)
            for alert in _ALERTS
            if str(alert.get("tenant_id")) == tenant_id
            and (plant_id is None or str(alert.get("plant_id")) == plant_id)
            and (asset_id is None or str(alert.get("asset_id")) == asset_id)
        ]
        if active_only:
            alerts = [alert for alert in alerts if str(alert.get("status", "open")).lower() == "open"]
        if status and status != "Todos":
            alerts = [alert for alert in alerts if str(alert.get("status", "open")) == status]
        return alerts

    def get_alert(
        self,
        tenant_asset: str,
        alert_key: str,
        *,
        pk: str | None = None,
        sk: str | None = None,
    ) -> dict[str, Any]:
        for alert in _ALERTS:
            if str(alert.get("tenant_asset")) == tenant_asset and str(alert.get("alert_key")) == alert_key:
                return copy.deepcopy(alert)
            if pk and sk and str(alert.get("pk")) == pk and str(alert.get("sk")) == sk:
                return copy.deepcopy(alert)
        return {}

    def update_status(
        self,
        tenant_asset: str,
        alert_key: str,
        new_status: str,
        user_name: str,
        note: str = "",
        action_taken: str = "",
        *,
        pk: str | None = None,
        sk: str | None = None,
    ) -> dict[str, Any]:
        for index, alert in enumerate(_ALERTS):
            key_matches = str(alert.get("tenant_asset")) == tenant_asset and str(alert.get("alert_key")) == alert_key
            legacy_matches = bool(pk and sk and str(alert.get("pk")) == pk and str(alert.get("sk")) == sk)
            if not key_matches and not legacy_matches:
                continue

            ts = now_utc()
            timeline = alert.get("timeline", [])
            if not isinstance(timeline, list):
                timeline = []
            timeline.append(
                {
                    "at": ts,
                    "by": user_name,
                    "from_status": alert.get("status"),
                    "to_status": new_status,
                    "note": note,
                    "action_taken": action_taken,
                }
            )
            updated = {
                **alert,
                "status": new_status,
                "last_status_update_at": ts,
                "last_status_update_by": user_name,
                "last_note": note,
                "last_action_taken": action_taken,
                "timeline": timeline,
            }
            _ALERTS[index] = updated
            return copy.deepcopy(updated)

        raise RuntimeError("Alerta não encontrado.")

    def create_manual_alert(
        self,
        tenant_id: str,
        plant_id: str,
        asset_id: str,
        asset_name: str,
        metric: str,
        status_label: str,
        value: float | None,
        threshold: float | None,
        recommended_action: str,
        created_by: str = "operador_demo",
        note: str = "",
    ) -> dict[str, Any]:
        if not str(recommended_action or "").strip():
            raise ValueError("Informe uma ação recomendada antes de criar o evento.")

        ts = now_utc()
        item = {
            "pk": self.legacy_pk(tenant_id, asset_id),
            "sk": f"ALERT#ACTIVE#MANUAL#{metric}#{ts}",
            "tenant_asset": self.tenant_asset(tenant_id, asset_id),
            "tenant_plant": f"{tenant_id}#{plant_id}",
            "alert_key": f"open#manual#{metric}#{ts}",
            "alert_id": f"{tenant_id}#{asset_id}#{metric}#manual#{ts}",
            "tenant_id": tenant_id,
            "plant_id": plant_id,
            "asset_id": asset_id,
            "asset_name": asset_name,
            "alert_type": "manual_event",
            "metric": metric,
            "value": value,
            "threshold": threshold,
            "severity": severity_from_status_label(status_label),
            "status_label": status_label or "ATENÇÃO",
            "status": "open",
            "probable_cause": metric,
            "confidence": 1.0,
            "evidence": [note] if note else ["Evento manual criado."],
            "first_detected_at": ts,
            "last_detected_at": ts,
            "updated_at": ts,
            "recommended_action": recommended_action,
            "created_by": created_by,
            "note": note,
            "timeline": [
                {
                    "at": ts,
                    "by": created_by,
                    "from_status": None,
                    "to_status": "open",
                    "note": note,
                    "action_taken": "Evento manual criado.",
                }
            ],
        }
        normalized = normalize_active_alert_item(item)
        _ALERTS.append(normalized)
        return copy.deepcopy(normalized)

    def put_latest_state(self, item: dict[str, Any]) -> None:
        state = _normalize_state(item)
        store = _state_store()
        for index, current in enumerate(store):
            if (
                str(current.get("tenant_id")) == str(state.get("tenant_id"))
                and str(current.get("asset_id")) == str(state.get("asset_id"))
            ):
                store[index] = state
                return
        store.append(state)

    def put_active_alert(self, item: dict[str, Any]) -> None:
        alert = normalize_active_alert_item(copy.deepcopy(item))
        self.clear_demo_alerts(str(alert.get("tenant_id")), str(alert.get("asset_id")))
        _ALERTS.append(alert)

    def clear_demo_alerts(self, tenant_id: str, asset_id: str) -> int:
        before = len(_ALERTS)
        _ALERTS[:] = [
            alert
            for alert in _ALERTS
            if not (
                str(alert.get("tenant_id")) == tenant_id
                and str(alert.get("asset_id")) == asset_id
                and alert.get("is_demo_case")
            )
        ]
        return before - len(_ALERTS)


class LocalDemoHistoryRepository:
    def put_minute_snapshot(self, latest_state: dict[str, Any], *, retention_days: int = 365) -> dict[str, Any]:
        return build_history_item(latest_state, retention_days=retention_days)

    def query_history(self, **_: Any) -> list[dict[str, Any]]:
        return []


def local_demo_enabled() -> bool:
    import os

    return os.getenv("DASHBOARD_DATA_MODE", "").strip().lower() in {"local", "demo", "offline"}


def create_local_demo_repository() -> LocalDemoRepository:
    return LocalDemoRepository()


def create_local_demo_history_repository() -> LocalDemoHistoryRepository:
    return LocalDemoHistoryRepository()
