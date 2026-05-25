from __future__ import annotations

import io
import unittest

from src.dashboard.config_repository import ConfigRepository
from src.dashboard.connection_validators import (
    validate_csv_file,
    validate_secret_reference,
    validate_signal_map_for_csv,
    validate_signal_map_for_source,
    validate_source_connection,
)


class ConnectionValidatorsTest(unittest.TestCase):
    def test_virtual_bench_returns_expected_contract(self) -> None:
        source = {
            "source_id": "virtual_bench_01",
            "source_type": "Simulação",
            "protocol": "Interno",
        }

        result = validate_source_connection(source)

        self.assertTrue(result.ok)
        self.assertIn("rpm", result.details["contract_metrics"])
        self.assertIn("severity_score", result.details["contract_metrics"])

    def test_secret_reference_accepts_safe_prefix(self) -> None:
        source = {
            "source_id": "opcua_edge_bridge_01",
            "source_type": "Gateway Edge",
            "protocol": "OPC UA via HTTPS",
            "credential_ref": "aws_secrets/opcua_edge_bridge_01",
        }

        result = validate_secret_reference(source)

        self.assertTrue(result.ok)
        self.assertFalse(result.details["secret_value_exposed"])

    def test_secret_reference_rejects_plain_text_style_reference(self) -> None:
        source = {
            "source_id": "opcua_edge_bridge_01",
            "source_type": "Gateway Edge",
            "protocol": "OPC UA via HTTPS",
            "credential_ref": "senha123",
        }

        result = validate_secret_reference(source)

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "atenção")

    def test_csv_validation_reads_required_columns(self) -> None:
        csv_file = io.BytesIO(
            b"asset_id,timestamp_utc,rpm,vibration_rms_mm_s,temperature_c\n"
            b"motor_001,2026-05-23T18:25:00Z,1779.57,2.96,67.91\n"
        )

        result = validate_csv_file(csv_file)

        self.assertTrue(result.ok)
        self.assertEqual(result.details["rows_preview_count"], 1)

    def test_csv_validation_reports_missing_required_columns(self) -> None:
        csv_file = io.BytesIO(b"asset_id,timestamp_utc,rpm\nmotor_001,2026-05-23T18:25:00Z,1779.57\n")

        result = validate_csv_file(csv_file)

        self.assertFalse(result.ok)
        self.assertIn("temperature_c", result.details["missing_columns"])

    def test_signal_map_for_source_uses_config_store(self) -> None:
        repo = ConfigRepository()
        data = repo.load()
        source = repo.get_data_source("opcua_edge_bridge_01", data)

        result = validate_signal_map_for_source(
            source or {},
            data["signal_map"],
            asset_id="motor_001",
        )

        self.assertTrue(result.ok)
        self.assertGreaterEqual(result.details["mapped_count"], 3)

    def test_signal_map_for_csv_checks_external_tags_as_columns(self) -> None:
        signal_map = [
            {
                "asset_id": "motor_001",
                "source_id": "csv_manual_01",
                "metric": "rpm",
                "external_tag": "rpm",
                "enabled": True,
            },
            {
                "asset_id": "motor_001",
                "source_id": "csv_manual_01",
                "metric": "temperature_c",
                "external_tag": "temperature_c",
                "enabled": True,
            },
        ]
        csv_file = io.BytesIO(
            b"asset_id,timestamp_utc,rpm,temperature_c\n"
            b"motor_001,2026-05-23T18:25:00Z,1779.57,67.91\n"
        )

        result = validate_signal_map_for_csv(
            signal_map,
            csv_file,
            asset_id="motor_001",
            source_id="csv_manual_01",
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.details["expected_tags"], ["rpm", "temperature_c"])

    def test_signal_map_for_csv_reports_empty_mapping_for_selected_source(self) -> None:
        csv_file = io.BytesIO(b"asset_id,timestamp_utc,rpm\nmotor_001,2026-05-23T18:25:00Z,1779.57\n")

        result = validate_signal_map_for_csv(
            [],
            csv_file,
            asset_id="motor_001",
            source_id="csv_manual_01",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "atenção")


if __name__ == "__main__":
    unittest.main()
