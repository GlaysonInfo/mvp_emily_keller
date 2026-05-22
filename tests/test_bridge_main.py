from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from edge_bridge.main import build_publishers, load_env_file
from edge_bridge.mqtt_publisher import MqttPublisher


class BridgeMainTest(unittest.TestCase):
    def test_load_env_file_sets_missing_values_without_overriding_existing_environment(self) -> None:
        old_value = os.environ.get("TENANT_ID")
        os.environ["TENANT_ID"] = "valor_existente"
        os.environ.pop("PLANT_ID", None)

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                env_path = Path(temp_dir) / ".env"
                env_path.write_text(
                    "TENANT_ID=cliente_demo\nPLANT_ID=lab_virtual\n# comentario\nINVALID\n",
                    encoding="utf-8",
                )

                load_env_file(env_path)

            self.assertEqual(os.environ["TENANT_ID"], "valor_existente")
            self.assertEqual(os.environ["PLANT_ID"], "lab_virtual")
        finally:
            if old_value is None:
                os.environ.pop("TENANT_ID", None)
            else:
                os.environ["TENANT_ID"] = old_value
            os.environ.pop("PLANT_ID", None)

    def test_build_mqtt_publisher_without_opening_network_connection(self) -> None:
        publishers = build_publishers(
            publish_mode="mqtt",
            mqtt_host="localhost",
            mqtt_port=1883,
            mqtt_topic="lab/demo",
            https_endpoint="",
        )

        self.assertEqual(len(publishers), 1)
        self.assertIsInstance(publishers[0], MqttPublisher)


if __name__ == "__main__":
    unittest.main()
