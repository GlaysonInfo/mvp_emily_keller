from __future__ import annotations

STATUS_TO_OPERATOR = {
    "NORMAL": ("Operação normal", "OK"),
    "RECUPERADO": ("Recuperado", "OK"),
    "ATENÇÃO": ("Atenção", "ATENÇÃO"),
    "ATENÇÃO ALTA": ("Atenção alta", "ALERTA"),
    "ALERTA": ("Alerta", "ALERTA"),
    "CRÍTICO": ("Crítico", "CRÍTICO"),
    "CRITICO": ("Crítico", "CRÍTICO"),
}


def operator_status_label(status: str) -> tuple[str, str]:
    return STATUS_TO_OPERATOR.get(str(status or "").upper(), (str(status or "-"), "INFO"))


def pretty_asset(asset_id: str, asset_name: str | None = None) -> str:
    if asset_name:
        return asset_name
    return str(asset_id or "-").replace("_", " ").title()
