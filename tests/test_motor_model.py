from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from simulator.contracts import EXPECTED_OPCUA_TAGS
from simulator.motor_model import FailureMode, MotorModel, MotorSimulator, Severity


SEVERITY_RANK = {
    "normal": 0,
    "warning": 1,
    "critical": 2,
}


class MotorModelFacadeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.motor = MotorModel(asset_id="motor_001", seed=42)

    def test_motor_model_returns_expected_tags(self) -> None:
        data = self.motor.simulate(elapsed_seconds=10)

        self.assertEqual(set(data.keys()), EXPECTED_OPCUA_TAGS)

    def test_normal_scenario_has_healthy_behavior(self) -> None:
        data = self.motor.simulate(elapsed_seconds=10)

        self.assertEqual(data["failure_mode"], "normal")
        self.assertGreaterEqual(data["rpm"], 1700)
        self.assertLessEqual(data["rpm"], 1850)
        self.assertLess(data["vibration_rms_mm_s"], 3.0)
        self.assertLess(data["temperature_c"], 70)
        self.assertLess(data["ultrasound_db"], 38)
        self.assertGreaterEqual(data["health_score"], 75)

    def test_lubrication_degradation_ultrasound_rises_first(self) -> None:
        early = self.motor.simulate(elapsed_seconds=65)
        late = self.motor.simulate(elapsed_seconds=115)

        self.assertEqual(early["failure_mode"], "lubrication_degradation")
        self.assertEqual(late["failure_mode"], "lubrication_degradation")
        self.assertGreater(late["ultrasound_db"], early["ultrasound_db"])
        self.assertGreaterEqual(late["temperature_c"], early["temperature_c"])
        self.assertGreaterEqual(SEVERITY_RANK[late["severity"]], SEVERITY_RANK[early["severity"]])

    def test_imbalance_increases_vibration_rms(self) -> None:
        early = self.motor.simulate(elapsed_seconds=125)
        late = self.motor.simulate(elapsed_seconds=175)

        self.assertEqual(early["failure_mode"], "imbalance")
        self.assertEqual(late["failure_mode"], "imbalance")
        self.assertGreater(late["vibration_rms_mm_s"], early["vibration_rms_mm_s"])
        self.assertGreaterEqual(SEVERITY_RANK[late["severity"]], SEVERITY_RANK[early["severity"]])

    def test_bearing_fault_increases_kurtosis_and_crest_factor(self) -> None:
        early = self.motor.simulate(elapsed_seconds=185)
        late = self.motor.simulate(elapsed_seconds=235)

        self.assertEqual(early["failure_mode"], "bearing_fault")
        self.assertEqual(late["failure_mode"], "bearing_fault")
        self.assertGreater(late["kurtosis"], early["kurtosis"])
        self.assertGreater(late["crest_factor"], early["crest_factor"])
        self.assertGreaterEqual(SEVERITY_RANK[late["severity"]], SEVERITY_RANK[early["severity"]])


class MotorSimulatorContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.simulator = MotorSimulator(scenario_duration_seconds=10.0, random_seed=7)

    def test_cycles_through_expected_failure_modes(self) -> None:
        samples = [self.simulator.sample(second) for second in (0.0, 10.0, 20.0, 30.0, 40.0)]

        self.assertEqual(samples[0].failure_mode, FailureMode.NORMAL)
        self.assertEqual(samples[1].failure_mode, FailureMode.LUBRICATION_DEGRADATION)
        self.assertEqual(samples[2].failure_mode, FailureMode.IMBALANCE)
        self.assertEqual(samples[3].failure_mode, FailureMode.BEARING_FAULT)
        self.assertEqual(samples[4].failure_mode, FailureMode.NORMAL)

    def test_canonical_payload_matches_mvp_contract(self) -> None:
        timestamp = datetime(2026, 5, 22, 13, 0, tzinfo=UTC)
        sample = self.simulator.sample(0.0, timestamp=timestamp)
        payload = sample.canonical_payload()
        metric_names = {metric["name"] for metric in payload["metrics"]}

        self.assertEqual(payload["tenant_id"], "cliente_demo")
        self.assertEqual(payload["plant_id"], "lab_virtual")
        self.assertEqual(payload["asset_id"], "motor_001")
        self.assertEqual(payload["timestamp"], "2026-05-22T13:00:00Z")
        self.assertEqual(payload["failure_mode_simulated"], "normal")
        self.assertEqual(len(payload["metrics"]), 9)
        self.assertIn("rpm", metric_names)
        self.assertIn("vibration_rms_mm_s", metric_names)
        self.assertIn("temperature_c", metric_names)
        self.assertIn("ultrasound_db", metric_names)

    def test_opcua_values_expose_expected_tags(self) -> None:
        values = self.simulator.sample(0.0).opcua_values()

        self.assertEqual(set(values), EXPECTED_OPCUA_TAGS)

    def test_lubrication_degradation_raises_ultrasound_before_critical_vibration(self) -> None:
        early = self.simulator.sample(11.0)
        late = self.simulator.sample(19.0)

        self.assertGreater(late.ultrasound_db, early.ultrasound_db)
        self.assertGreater(late.temperature_c, early.temperature_c)
        self.assertLess(late.vibration_rms_mm_s, 4.0)
        self.assertEqual(late.severity, Severity.WARNING)

    def test_imbalance_raises_vibration_with_moderate_kurtosis(self) -> None:
        late = self.simulator.sample(29.0)

        self.assertEqual(late.failure_mode, FailureMode.IMBALANCE)
        self.assertGreater(late.vibration_rms_mm_s, 4.0)
        self.assertLess(late.kurtosis, 4.5)
        self.assertEqual(late.severity, Severity.CRITICAL)

    def test_bearing_fault_raises_kurtosis_and_crest_factor(self) -> None:
        late = self.simulator.sample(39.0)

        self.assertEqual(late.failure_mode, FailureMode.BEARING_FAULT)
        self.assertGreater(late.kurtosis, 5.0)
        self.assertGreater(late.crest_factor, 4.5)
        self.assertEqual(late.severity, Severity.CRITICAL)


if __name__ == "__main__":
    unittest.main()

