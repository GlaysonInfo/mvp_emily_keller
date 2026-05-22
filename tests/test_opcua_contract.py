from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from simulator.contracts import EXPECTED_OPCUA_TAGS, OPCUA_TAGS
from simulator.opcua_server import OPCUA_TAGS as SERVER_OPCUA_TAGS


class OpcUaContractTest(unittest.TestCase):
    def test_opcua_tag_contract_has_expected_11_tags(self) -> None:
        self.assertEqual(len(EXPECTED_OPCUA_TAGS), 11)
        self.assertIn("rpm", EXPECTED_OPCUA_TAGS)
        self.assertIn("failure_mode", EXPECTED_OPCUA_TAGS)

    def test_server_uses_shared_tag_contract(self) -> None:
        self.assertEqual(SERVER_OPCUA_TAGS, OPCUA_TAGS)
        self.assertEqual(set(SERVER_OPCUA_TAGS), EXPECTED_OPCUA_TAGS)


if __name__ == "__main__":
    unittest.main()

