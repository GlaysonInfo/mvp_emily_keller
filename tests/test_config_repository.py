from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from src.dashboard.config_repository import ConfigRepository, DEFAULT_CONFIG, normalize_config


def sample_config() -> dict:
    data = deepcopy(DEFAULT_CONFIG)
    data["data_sources"] = [
        {
            "source_id": "opcua_edge_bridge_01",
            "source_name": "Bridge OPC UA / HTTPS",
            "source_type": "Gateway Edge",
            "protocol": "OPC UA via HTTPS",
            "endpoint": "https://edge-gateway.local/ingest",
            "credential_ref": "aws_secrets/opcua_edge_bridge_01",
        }
    ]
    data["assets"] = [
        {
            "asset_id": "motor_001",
            "asset_name": "Motor Linha 1",
            "source_id": "opcua_edge_bridge_01",
            "status": "Ativo",
        },
        {
            "asset_id": "compressor_001",
            "asset_name": "Compressor de Ar 1",
            "source_id": "opcua_edge_bridge_01",
            "status": "Ativo",
        },
    ]
    data["signal_map"] = [
        {
            "asset_id": "motor_001",
            "source_id": "opcua_edge_bridge_01",
            "metric": "vibration_rms_mm_s",
            "external_tag": "Motor001.VIB_RMS",
            "enabled": True,
        }
    ]
    data["sensors"] = [
        {
            "sensor_id": "sensor_motor_001",
            "asset_id": "motor_001",
            "source_id": "opcua_edge_bridge_01",
            "metric": "vibration_rms_mm_s",
        }
    ]
    data["signal_map"][0]["sensor_id"] = "sensor_motor_001"
    return data


class ConfigRepositoryTest(unittest.TestCase):
    def test_repository_reads_known_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config_store.json"
            path.write_text(json.dumps(sample_config(), ensure_ascii=False), encoding="utf-8")
            repo = ConfigRepository(path)
            data = repo.load()

            self.assertEqual(data["client"]["tenant_id"], "cliente_demo")
            self.assertEqual(data["plant"]["plant_id"], "lab_virtual")
            self.assertEqual(repo.default_asset_id(data), "motor_001")
            self.assertEqual(repo.environment_label(data), "Demonstração - Bancada Virtual")
            self.assertEqual(repo.validate(data), [])

    def test_links_assets_to_sources_and_signal_map(self) -> None:
        repo = ConfigRepository()
        data = sample_config()

        compressor = repo.get_asset("compressor_001", data)
        source = repo.get_data_source("opcua_edge_bridge_01", data)
        motor_signals = repo.signal_map_for_asset("motor_001", data)
        motor_sensors = repo.sensors_for_asset("motor_001", data)

        self.assertIsNotNone(compressor)
        self.assertEqual(compressor["source_id"], "opcua_edge_bridge_01")
        self.assertIsNotNone(source)
        self.assertEqual(source["protocol"], "OPC UA via HTTPS")
        self.assertIn("vibration_rms_mm_s", {signal["metric"] for signal in motor_signals})
        self.assertEqual(motor_sensors[0]["sensor_id"], "sensor_motor_001")

    def test_normalize_accepts_documentation_asset_signal_map_alias(self) -> None:
        data = normalize_config(
            {
                "asset_signal_map": [
                    {
                        "asset_id": "motor_001",
                        "source_id": "opcua_edge_bridge_01",
                        "metric": "rpm",
                    }
                ]
            }
        )

        self.assertEqual(data["signal_map"][0]["metric"], "rpm")

    def test_normalize_migrates_legacy_expected_range_to_process_range(self) -> None:
        data = normalize_config(
            {
                "sensors": [
                    {
                        "sensor_id": "sensor_01",
                        "expected_min": 1,
                        "expected_max": 8,
                    }
                ]
            }
        )

        self.assertEqual(data["sensors"][0]["process_expected_min"], 1)
        self.assertEqual(data["sensors"][0]["process_expected_max"], 8)

    def test_save_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config_store.json"
            repo = ConfigRepository(path)
            data = repo.load()
            data["client"]["tenant_id"] = "cliente_teste"

            repo.save(data)

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["client"]["tenant_id"], "cliente_teste")
            self.assertEqual(ConfigRepository(path).load()["client"]["tenant_id"], "cliente_teste")

    def test_save_versioned_records_actor_reason_and_entity_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config_store.json"
            repo = ConfigRepository(path)
            baseline = sample_config()
            repo.save(baseline)
            updated = repo.load()
            updated["assets"][0]["criticality"] = "Crítica"

            revision = repo.save_versioned(
                updated,
                change_type="technical_registry.upsert",
                target="asset:motor_001",
                reason="Ajuste após inspeção de campo.",
                actor={
                    "email": "admin@sentinela.com.br",
                    "role": "admin",
                    "tenant_id": "cliente_demo",
                },
                tenant_id="cliente_demo",
                plant_id="lab_virtual",
            )

            self.assertIsNotNone(revision)
            self.assertEqual(revision["revision"], 1)
            self.assertEqual(revision["changed_by"], "admin@sentinela.com.br")
            self.assertEqual(revision["reason"], "Ajuste após inspeção de campo.")
            self.assertEqual(revision["changes"][0]["section"], "assets")
            self.assertEqual(revision["changes"][0]["operation"], "updated")
            self.assertIsNone(revision["changes"][0]["before"].get("criticality"))
            self.assertEqual(revision["changes"][0]["after"]["criticality"], "Crítica")

            saved = repo.load()
            self.assertEqual(saved["configuration_version"], 1)
            self.assertEqual(len(repo.technical_change_history(saved)), 1)
            self.assertFalse(path.with_suffix(".json.tmp").exists())

    def test_save_versioned_does_not_create_revision_without_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config_store.json"
            repo = ConfigRepository(path)
            repo.save(sample_config())

            revision = repo.save_versioned(
                repo.load(),
                change_type="technical_registry.upsert",
                target="asset:motor_001",
                reason="Reenvio sem mudança.",
            )

            self.assertIsNone(revision)
            self.assertEqual(repo.load()["configuration_version"], 0)
            self.assertEqual(repo.technical_change_history(), [])

    def test_save_versioned_requires_change_reason(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config_store.json"
            repo = ConfigRepository(path)
            repo.save(sample_config())
            updated = repo.load()
            updated["assets"][0]["status"] = "Inativo"

            with self.assertRaisesRegex(ValueError, "motivo"):
                repo.save_versioned(
                    updated,
                    change_type="technical_registry.upsert",
                    target="asset:motor_001",
                    reason=" ",
                )

    def test_validate_reports_missing_source_reference(self) -> None:
        repo = ConfigRepository()
        data = sample_config()
        data["assets"][0]["source_id"] = "fonte_inexistente"

        issues = repo.validate(data)

        self.assertIn("fonte_inexistente", issues[0]["message"])

    def test_validate_reports_missing_sensor_reference(self) -> None:
        repo = ConfigRepository()
        data = sample_config()
        data["signal_map"][0]["sensor_id"] = "sensor_inexistente"

        issues = repo.validate(data)

        self.assertTrue(any("sensor_inexistente" in issue["message"] for issue in issues))

    def test_validate_reports_invalid_or_incompatible_sensor_ranges(self) -> None:
        repo = ConfigRepository()
        data = sample_config()
        data["sensors"][0].update(
            {
                "process_expected_min": -5,
                "process_expected_max": 12,
                "instrument_range_min": 0,
                "instrument_range_max": 10,
            }
        )

        issues = repo.validate(data)

        self.assertTrue(any("fora da faixa física" in issue["message"] for issue in issues))

        data["sensors"][0]["instrument_range_min"] = 20
        data["sensors"][0]["instrument_range_max"] = 10
        issues = repo.validate(data)

        self.assertTrue(any("faixa física do instrumento inválida" in issue["message"] for issue in issues))

    def test_validate_allows_same_metric_for_distinct_sensors_on_asset(self) -> None:
        repo = ConfigRepository()
        data = sample_config()
        data["sensors"].append(
            {
                "sensor_id": "sensor_motor_002",
                "asset_id": "motor_001",
                "source_id": "opcua_edge_bridge_01",
                "metric": "vibration_rms_mm_s",
            }
        )
        data["signal_map"].append(
            {
                "asset_id": "motor_001",
                "source_id": "opcua_edge_bridge_01",
                "sensor_id": "sensor_motor_002",
                "metric": "vibration_rms_mm_s",
                "external_tag": "Motor001.VIB_RMS_NDE",
            }
        )

        issues = repo.validate(data)

        self.assertFalse(any("Mapeamento duplicado" in issue["message"] for issue in issues))


if __name__ == "__main__":
    unittest.main()
