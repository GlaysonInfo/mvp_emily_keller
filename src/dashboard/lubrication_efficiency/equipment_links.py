from __future__ import annotations

from typing import Any

try:
    from dashboard.lubrication.lubrication_labels import outlet_label
except ImportError:  # pragma: no cover - supports local test imports.
    from src.dashboard.lubrication.lubrication_labels import outlet_label


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value in [None, ""]:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _state_by_asset_id(equipment_states: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(state.get("asset_id")): state for state in equipment_states if state.get("asset_id")}


def _outlet_by_id(lubrication_state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(outlet.get("outlet_id")): outlet
        for outlet in lubrication_state.get("outlets", [])
        if outlet.get("outlet_id")
    }


def _state_health(state: dict[str, Any]) -> Any:
    if not state:
        return "-"

    if state.get("health_score") not in [None, ""]:
        return state.get("health_score")

    metrics = state.get("metrics")
    if isinstance(metrics, dict) and metrics.get("health_score") not in [None, ""]:
        return metrics.get("health_score")

    return "-"


def normalize_equipment_links(config: dict[str, Any]) -> list[dict[str, Any]]:
    links = []
    lubrication_system_id = str(config.get("asset_id") or "sistema_lubrificacao_01")

    for raw in config.get("equipment_links", []) or []:
        asset_id = str(raw.get("asset_id") or "").strip()
        outlet_id = str(raw.get("outlet_id") or "").strip()

        if not asset_id or not outlet_id:
            continue

        link = {
            "link_id": str(raw.get("link_id") or f"{asset_id}_{outlet_id}"),
            "enabled": bool(raw.get("enabled", True)),
            "asset_id": asset_id,
            "asset_name": str(raw.get("asset_name") or asset_id),
            "outlet_id": outlet_id,
            "outlet_name": str(raw.get("outlet_name") or outlet_label(outlet_id)),
            "lubrication_system_id": str(raw.get("lubrication_system_id") or lubrication_system_id),
            "grease_type": str(raw.get("grease_type") or "-"),
            "target_grease_g_per_cycle": _to_float(raw.get("target_grease_g_per_cycle")),
            "cycle_interval_h": _to_float(raw.get("cycle_interval_h")),
            "baseline_status": str(raw.get("baseline_status") or "marco_zero_pendente"),
            "objective": str(raw.get("objective") or ""),
        }
        links.append(link)

    return links


def enabled_equipment_links(config: dict[str, Any]) -> list[dict[str, Any]]:
    return [link for link in normalize_equipment_links(config) if link["enabled"]]


def filter_linked_equipment_states(
    equipment_states: list[dict[str, Any]],
    links: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not links:
        return equipment_states

    linked_asset_ids = {link["asset_id"] for link in links}
    return [state for state in equipment_states if state.get("asset_id") in linked_asset_ids]


def equipment_link_rows(
    links: list[dict[str, Any]],
    equipment_states: list[dict[str, Any]],
    lubrication_state: dict[str, Any],
) -> list[dict[str, Any]]:
    states = _state_by_asset_id(equipment_states)
    outlets = _outlet_by_id(lubrication_state)
    rows = []

    for link in links:
        state = states.get(link["asset_id"], {})
        outlet = outlets.get(link["outlet_id"], {})

        rows.append(
            {
                "Equipamento": link["asset_name"],
                "Asset ID": link["asset_id"],
                "Saída": link["outlet_name"],
                "Outlet ID": link["outlet_id"],
                "Graxa": link["grease_type"],
                "Dose alvo (g/ciclo)": link["target_grease_g_per_cycle"],
                "Intervalo (h)": link["cycle_interval_h"],
                "Marco zero": link["baseline_status"],
                "Status equipamento": state.get("status_label") or "-",
                "Saúde": _state_health(state),
                "Status saída": outlet.get("severity") or outlet.get("status_label") or outlet.get("status") or "-",
                "Pico saída": outlet.get("peak_pressure_bar") or "-",
                "Objetivo": link["objective"],
            }
        )

    return rows
