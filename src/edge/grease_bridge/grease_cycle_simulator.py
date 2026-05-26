
import random
from datetime import datetime, timezone


def now_utc():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def jitter(value, sigma):
    return round(random.normalvariate(value, sigma), 2)


def generate_grease_cycle_payload(
    tenant_id="cliente_demo",
    plant_id="lab_virtual",
    asset_id="sistema_lubrificacao_01",
    source_id="grease_gateway_01",
):
    ts = now_utc()
    return {
        "tenant_id": tenant_id,
        "plant_id": plant_id,
        "asset_id": asset_id,
        "source_id": source_id,
        "timestamp_utc": ts,
        "cycle_id": f"cycle_{ts.replace(':', '').replace('-', '').replace('.', '')}",
        "metrics": {
            "pressure_saida_graxa_01_bar": jitter(84.2, 2),
            "pressure_saida_graxa_02_bar": jitter(91.7, 2),
            "pressure_saida_graxa_03_bar": jitter(7.8, 0.8),
            "pressure_saida_graxa_04_bar": jitter(146.5, 5),
            "peak_saida_graxa_01_bar": jitter(102.3, 3),
            "peak_saida_graxa_02_bar": jitter(108.1, 3),
            "peak_saida_graxa_03_bar": jitter(9.2, 0.4),
            "peak_saida_graxa_04_bar": jitter(181.2, 8),
            "min_saida_graxa_01_bar": jitter(2, 0.5),
            "min_saida_graxa_02_bar": jitter(2, 0.5),
            "min_saida_graxa_03_bar": jitter(0.2, 0.1),
            "min_saida_graxa_04_bar": jitter(4, 0.8),
            "rise_time_saida_graxa_01_sec": jitter(3.2, 0.3),
            "rise_time_saida_graxa_02_sec": jitter(3.5, 0.3),
            "rise_time_saida_graxa_03_sec": jitter(8.9, 1),
            "rise_time_saida_graxa_04_sec": jitter(2.1, 0.3),
            "decay_time_saida_graxa_01_sec": jitter(4.8, 0.5),
            "decay_time_saida_graxa_02_sec": jitter(5.1, 0.5),
            "decay_time_saida_graxa_03_sec": jitter(2.4, 0.4),
            "decay_time_saida_graxa_04_sec": jitter(18.6, 1.8),
        },
    }


if __name__ == "__main__":
    import json

    print(json.dumps(generate_grease_cycle_payload(), ensure_ascii=False, indent=2))
