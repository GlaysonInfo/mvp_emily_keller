from __future__ import annotations

import os
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import boto3


def to_decimal(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(round(value, 4)))

    if isinstance(value, dict):
        return {key: to_decimal(item) for key, item in value.items()}

    if isinstance(value, list):
        return [to_decimal(item) for item in value]

    return value


def main() -> None:
    profile = os.getenv("AWS_PROFILE") or None
    region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
    table_name = os.getenv("CONDITION_HISTORY_TABLE", "condition_history")

    session = boto3.Session(profile_name=profile, region_name=region)
    table = session.resource("dynamodb").Table(table_name)

    tenant_id = os.getenv("TENANT_ID", "cliente_demo")
    plant_id = os.getenv("PLANT_ID", "lab_virtual")
    asset_id = os.getenv("ASSET_ID", "motor_001")
    tenant_asset = f"{tenant_id}#{asset_id}"
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    items: list[dict[str, Any]] = []

    for index in range(140):
        ts = now - timedelta(minutes=140 - index)

        if index < 120:
            status = "NORMAL"
            mode = "synthetic_baseline"
            temp = random.normalvariate(58, 1.8)
            vib = random.normalvariate(2.1, 0.2)
            ultra = random.normalvariate(33, 2)
            health = random.normalvariate(92, 2)
        else:
            status = "ATENÇÃO"
            mode = "thermal_stress"
            temp = random.normalvariate(76, 2.2)
            vib = random.normalvariate(2.4, 0.25)
            ultra = random.normalvariate(43, 3)
            health = random.normalvariate(70, 3)

        severity = 100 - health
        timestamp = ts.isoformat().replace("+00:00", "Z")
        items.append(
            {
                "tenant_asset": tenant_asset,
                "ts_utc_minute": timestamp,
                "tenant_id": tenant_id,
                "plant_id": plant_id,
                "asset_id": asset_id,
                "status_label": status,
                "mode": mode,
                "rpm": random.normalvariate(1780, 3),
                "vibration_rms_mm_s": vib,
                "temperature_c": temp,
                "ultrasound_db": ultra,
                "kurtosis_index": random.normalvariate(2.6, 0.2),
                "crest_factor_index": random.normalvariate(2.5, 0.2),
                "vibration_peak_g": random.normalvariate(0.45, 0.08),
                "hourmeter_h": 1280 + index / 60,
                "health_score": health,
                "severity_score": severity,
                "updated_at": timestamp,
            }
        )

    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=to_decimal(item))

    print(f"Histórico sintético inserido: {len(items)} registros em {table_name} para {tenant_asset}")


if __name__ == "__main__":
    main()
