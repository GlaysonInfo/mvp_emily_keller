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

        self.assertIsNotNone(compressor)
        self.assertEqual(compressor["source_id"], "opcua_edge_bridge_01")
        self.assertIsNotNone(source)
        self.assertEqual(source["protocol"], "OPC UA via HTTPS")
        self.assertIn("vibration_rms_mm_s", {signal["metric"] for signal in motor_signals})

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

    def test_validate_reports_missing_source_reference(self) -> None:
        repo = ConfigRepository()
        data = sample_config()
        data["assets"][0]["source_id"] = "fonte_inexistente"

        issues = repo.validate(data)

        self.assertIn("fonte_inexistente", issues[0]["message"])


if __name__ == "__main__":
    unittest.main()
