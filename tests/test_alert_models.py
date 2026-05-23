from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rules_engine.alert_models import Alert


class AlertModelsTest(unittest.TestCase):
    def test_alert_to_dict_contains_required_contract(self) -> None:
        alert = Alert(
            alert_type="imbalance",
            severity="critical",
            status="open",
            probable_cause="Possivel desbalanceamento",
            confidence=0.82,
            evidence=[
                "Vibracao RMS acima de 4.0 mm/s",
                "Ultrassom dentro da faixa esperada",
            ],
            recommended_action="Verificar balanceamento, fixacao, acoplamento e base do motor",
            tenant_id="cliente_demo",
            plant_id="lab_virtual",
            asset_id="motor_001",
        )

        data = alert.to_dict()

        self.assertEqual(data["alert_type"], "imbalance")
        self.assertEqual(data["severity"], "critical")
        self.assertEqual(data["status"], "open")
        self.assertEqual(data["probable_cause"], "Possivel desbalanceamento")
        self.assertEqual(data["confidence"], 0.82)
        self.assertEqual(data["asset_id"], "motor_001")
        self.assertIn("evidence", data)
        self.assertIn("recommended_action", data)

    def test_alert_rejects_invalid_confidence(self) -> None:
        with self.assertRaises(ValueError):
            Alert(
                alert_type="imbalance",
                severity="critical",
                status="open",
                probable_cause="Possivel desbalanceamento",
                confidence=1.5,
                evidence=["Evidencia"],
                recommended_action="Acao",
            )

    def test_alert_rejects_missing_evidence(self) -> None:
        with self.assertRaises(ValueError):
            Alert(
                alert_type="imbalance",
                severity="critical",
                status="open",
                probable_cause="Possivel desbalanceamento",
                confidence=0.82,
                evidence=[],
                recommended_action="Acao",
            )


if __name__ == "__main__":
    unittest.main()
