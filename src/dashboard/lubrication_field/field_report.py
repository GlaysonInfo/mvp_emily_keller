
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone


def build_lubrication_report_text(cycles: list[dict], alerts: list[dict], config: dict) -> str:
    system = config.get("lubrication_system", {})
    lines = []

    lines.append("RELATÓRIO DE MONITORAMENTO DE LUBRIFICAÇÃO POR PRESSÃO")
    lines.append("")
    lines.append(f"Sistema: {system.get('asset_name', '-')}")
    lines.append(f"Asset ID: {system.get('asset_id', '-')}")
    lines.append(f"Gerado em: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}")
    lines.append("")
    lines.append(f"Ciclos analisados: {len(cycles)}")
    lines.append(f"Alertas registrados: {len(alerts)}")
    lines.append("")

    if cycles:
        last = cycles[0]
        lines.append("ÚLTIMO CICLO")
        lines.append(f"Data/Hora: {last.get('cycle_timestamp')}")
        lines.append(f"Status: {last.get('status_label')}")
        lines.append(f"Maior pressão: {last.get('max_pressure_bar')} bar")
        lines.append(f"Maior score: {last.get('max_anomaly_score')}")
        lines.append("")

        lines.append("SAÍDAS DO ÚLTIMO CICLO")
        for outlet in last.get("outlets", []):
            lines.append(
                f"- {outlet.get('outlet_id')}: "
                f"pico {outlet.get('peak_pressure_bar')} bar, "
                f"subida {outlet.get('rise_time_sec')} s, "
                f"alívio {outlet.get('decay_time_sec')} s, "
                f"status {outlet.get('severity')}"
            )

    if alerts:
        lines.append("")
        lines.append("ALERTAS")
        for alert in alerts:
            lines.append(
                f"- {alert.get('status_label')} | {alert.get('outlet_id')} | "
                f"{alert.get('description')} | Ação: {alert.get('recommended_action')}"
            )

    return "\n".join(lines)


def cycles_to_csv(cycles: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "cycle_timestamp",
            "cycle_id",
            "status_label",
            "outlet_count",
            "normal_count",
            "attention_count",
            "alert_count",
            "critical_count",
            "max_pressure_bar",
            "max_anomaly_score",
        ],
        delimiter=";"
    )
    writer.writeheader()

    for cycle in cycles:
        writer.writerow({
            "cycle_timestamp": cycle.get("cycle_timestamp"),
            "cycle_id": cycle.get("cycle_id"),
            "status_label": cycle.get("status_label"),
            "outlet_count": cycle.get("outlet_count"),
            "normal_count": cycle.get("normal_count"),
            "attention_count": cycle.get("attention_count"),
            "alert_count": cycle.get("alert_count"),
            "critical_count": cycle.get("critical_count"),
            "max_pressure_bar": cycle.get("max_pressure_bar"),
            "max_anomaly_score": cycle.get("max_anomaly_score"),
        })

    return output.getvalue()


def report_to_json(cycles: list[dict], alerts: list[dict], config: dict) -> str:
    return json.dumps(
        {
            "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "config": config,
            "cycles": cycles,
            "alerts": alerts,
        },
        ensure_ascii=False,
        indent=2
    )
