from __future__ import annotations

import unittest
from datetime import datetime

from src.dashboard.intelligence_repository import OperationalIntelligenceRepository


class FakeStateRepository:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def get_latest_state(self, *, tenant_id: str, asset_id: str) -> dict:
        self.requests.append({"tenant_id": tenant_id, "asset_id": asset_id})
        return {"tenant_id": tenant_id, "asset_id": asset_id, "status_label": "ATENÇÃO"}


class FakeHistoryRepository:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def query_history(self, *, tenant_id: str, asset_id: str, start_utc: datetime, end_utc: datetime) -> list[dict]:
        self.requests.append(
            {
                "tenant_id": tenant_id,
                "asset_id": asset_id,
                "start_utc": start_utc,
                "end_utc": end_utc,
            }
        )
        return [{"asset_id": asset_id, "temperature_c": 58}]


class IntelligenceRepositoryTest(unittest.TestCase):
    def test_repository_delegates_to_dashboard_and_history_repositories(self) -> None:
        state_repo = FakeStateRepository()
        history_repo = FakeHistoryRepository()
        repo = OperationalIntelligenceRepository(state_repository=state_repo, history_repository=history_repo)

        state = repo.get_current_state("cliente_demo", "motor_001")
        history = repo.query_history("cliente_demo", "motor_001", hours=6)

        self.assertEqual(state["status_label"], "ATENÇÃO")
        self.assertEqual(history, [{"asset_id": "motor_001", "temperature_c": 58}])
        self.assertEqual(state_repo.requests, [{"tenant_id": "cliente_demo", "asset_id": "motor_001"}])
        self.assertEqual(history_repo.requests[0]["tenant_id"], "cliente_demo")
        self.assertEqual(history_repo.requests[0]["asset_id"], "motor_001")
        self.assertLess(history_repo.requests[0]["start_utc"], history_repo.requests[0]["end_utc"])


if __name__ == "__main__":
    unittest.main()
