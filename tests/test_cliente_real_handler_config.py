from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.api.condition_ingest_models import ConditionIngestPayload
from src.api.condition_registry_validation import validate_condition_payload_against_registry
from src.dashboard.config_repository import ConfigRepository
from src.edge.condition_bridge_field.config_store import (
    load_condition_field_config,
    validate_condition_field_config,
)
from src.edge.condition_bridge_field.gateway_client import ConditionGatewayClient
from src.edge.condition_bridge_field.payload_builder import build_condition_payloads


REGISTRY_CONFIG = Path("config/cliente_real_indoor_config_store.json")
FIELD_CONFIG = Path("config/cliente_real_indoor_condition_config.json")
PLATFORM_ADMIN_UI = Path("src/dashboard/platform_admin_ui.py")


class ClienteRealHandlerConfigTest(unittest.TestCase):
    def test_platform_admin_ui_exposes_process_instrument_options(self) -> None:
        source = PLATFORM_ADMIN_UI.read_text(encoding="utf-8")

        self.assertIn("Instrumento de processo", source)
        self.assertIn("Tanque / silo", source)
        self.assertIn("Nivel radar", source)
        self.assertIn("level_percent", source)
        self.assertIn("measurement_reliability_percent", source)

    def test_cliente_real_handler_operational_registry_is_valid(self) -> None:
        repo = ConfigRepository(REGISTRY_CONFIG)
        config = repo.load()
        issues = repo.validate(config)

        self.assertEqual([], [issue for issue in issues if issue["severity"] == "error"])
        self.assertEqual("cliente_real", config["client"]["tenant_id"])
        self.assertEqual("indoor", config["plant"]["plant_id"])
        self.assertEqual(
            "Instrumento de processo",
            repo.get_asset("handler_vegapuls6x_01", config)["asset_type"],
        )

    def test_cliente_real_handler_field_config_builds_payload_from_sample(self) -> None:
        config = load_condition_field_config(str(FIELD_CONFIG))
        issues = validate_condition_field_config(config)
        raw = ConditionGatewayClient(config).read_raw()

        payloads = build_condition_payloads(config, raw)
        payload = next(item for item in payloads if item["asset_id"] == "handler_vegapuls6x_01")
        metrics = {metric["name"]: metric for metric in payload["metrics"]}

        self.assertEqual([], [issue for issue in issues if issue["level"] == "ERRO"])
        self.assertEqual("cliente_real", payload["tenant_id"])
        self.assertEqual("indoor", payload["plant_id"])
        self.assertEqual("handler_vegapuls6x_gateway_01", payload["source"])
        self.assertEqual(62.5, metrics["level_percent"]["value"])
        self.assertEqual("m", metrics["distance_m"]["unit"])
        self.assertEqual(0.0, metrics["device_state"]["value"])

    def test_cliente_real_handler_payload_matches_registry(self) -> None:
        registry_config = json.loads(REGISTRY_CONFIG.read_text(encoding="utf-8"))
        field_config = load_condition_field_config(str(FIELD_CONFIG))
        raw = ConditionGatewayClient(field_config).read_raw()
        payload = build_condition_payloads(field_config, raw)[0]

        warnings = validate_condition_payload_against_registry(
            ConditionIngestPayload(**payload),
            config=registry_config,
        )

        self.assertEqual([], warnings)


if __name__ == "__main__":
    unittest.main()
