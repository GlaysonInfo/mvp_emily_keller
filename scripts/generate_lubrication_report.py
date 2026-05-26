
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.dashboard.lubrication.lubrication_repository import LubricationRepository
from src.dashboard.lubrication_field.field_config_store import load_field_config
from src.dashboard.lubrication_field.field_report import build_lubrication_report_text, cycles_to_csv, report_to_json


def main():
    config = load_field_config("config/field_lubrication_config.example.json")
    client = config["client"]
    system = config["lubrication_system"]

    repo = LubricationRepository()
    cycles = repo.list_cycles(client["tenant_id"], system["asset_id"], limit=100)
    alerts = repo.list_alerts(client["tenant_id"], system["asset_id"])

    out = Path("reports")
    out.mkdir(exist_ok=True)

    (out / "relatorio_lubrificacao.txt").write_text(
        build_lubrication_report_text(cycles, alerts, config),
        encoding="utf-8"
    )
    (out / "ciclos_lubrificacao.csv").write_text(
        cycles_to_csv(cycles),
        encoding="utf-8-sig"
    )
    (out / "relatorio_lubrificacao.json").write_text(
        report_to_json(cycles, alerts, config),
        encoding="utf-8"
    )

    print("Relatórios gerados em ./reports")


if __name__ == "__main__":
    main()
