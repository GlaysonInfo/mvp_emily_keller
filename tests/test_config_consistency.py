from __future__ import annotations

import unittest
from copy import deepcopy

from src.dashboard.config_consistency import is_valid_technical_id, validate_config_consistency
from src.dashboard.config_repository import DEFAULT_CONFIG


def consistent_config() -> dict:
    data = deepcopy(DEFAULT_CONFIG)
    data["data_sources"] = [
        {
            "source_id": "opcua_edge_bridge_01",
            "source_name": "Bridge OPC UA / HTTPS",
            "protocol": "OPC UA via HTTPS",
            "endpoint": "https://edge-gateway.local/ingest",
            "status": "Ativa",
        }
    ]
    data["assets"] = [
        {
            "tenant_id": "cliente_demo",
            "plant_id": "lab_virtual",
            "asset_id": "motor_001",
            "asset_name": "Motor Linha 1",
            "source_id": "opcua_edge_bridge_01",
            "nominal_rpm": 1800,
            "status": "Ativo",
        }
    ]
    data["signal_map"] = [
        {
            "asset_id": "motor_001",
            "source_id": "opcua_edge_bridge_01",
            "metric": "rpm",
            "external_tag": "Motor001.RPM",
            "enabled": True,
        },
        {
            "asset_id": "motor_001",
            "source_id": "opcua_edge_bridge_01",
            "metric": "vibration_rms_mm_s",
            "external_tag": "Motor001.VIB_RMS",
            "enabled": True,
        },
        {
            "asset_id": "motor_001",
            "source_id": "opcua_edge_bridge_01",
            "metric": "temperature_c",
            "external_tag": "Motor001.TEMP",
            "enabled": True,
        },
    ]
    data["parameters_alerts"] = [
        {
            "asset_id": "motor_001",
            "metric": "temperature_c",
            "attention_min": 70,
            "alert_min": 80,
            "critical_min": 90,
            "enabled": True,
        }
    ]
    return data


class ConfigConsistencyTest(unittest.TestCase):
    def test_technical_id_validation(self) -> None:
        self.assertTrue(is_valid_technical_id("cliente_demo"))
        self.assertTrue(is_valid_technical_id("motor-001"))
        self.assertFalse(is_valid_technical_id("Emily"))
        self.assertFalse(is_valid_technical_id("cliente demonstração"))
        self.assertFalse(is_valid_technical_id("cliënté"))

    def test_consistent_config_returns_ok(self) -> None:
        result = validate_config_consistency(consistent_config())

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], 0)
        self.assertEqual(result["warnings"], 0)

    def test_invalid_tenant_and_mismatched_assets_are_critical(self) -> None:
        data = consistent_config()
        data["client"]["tenant_id"] = "Emily"
        data["assets"][0]["tenant_id"] = "cliente_demo"

        result = validate_config_consistency(data)
        messages = " ".join(issue["message"] for issue in result["issues"])

        self.assertEqual(result["status"], "critical")
        self.assertIn("tenant_id inválido", messages)
        self.assertIn("diferente do cliente", messages)

    def test_missing_signal_and_rule_limits_are_warnings(self) -> None:
        data = consistent_config()
        data["signal_map"] = data["signal_map"][:1]
        data["parameters_alerts"][0] = {
            "asset_id": "motor_001",
            "metric": "temperature_c",
            "enabled": True,
        }

        result = validate_config_consistency(data)
        messages = " ".join(issue["message"] for issue in result["issues"])

        self.assertEqual(result["status"], "warning")
        self.assertIn("métricas mínimas", messages)
        self.assertIn("sem limites técnicos", messages)

    def test_missing_source_reference_is_critical(self) -> None:
        data = consistent_config()
        data["assets"][0]["source_id"] = "fonte_inexistente"

        result = validate_config_consistency(data)

        self.assertEqual(result["status"], "critical")
        self.assertIn("fonte_inexistente", result["issues"][0]["message"])


if __name__ == "__main__":
    unittest.main()
