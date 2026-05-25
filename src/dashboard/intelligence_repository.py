from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

try:
    from dashboard.dynamodb_repository import DashboardRepository, create_repository_from_env
    from dashboard.history_repository import ConditionHistoryRepository, create_history_repository_from_env
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.dynamodb_repository import DashboardRepository, create_repository_from_env
    from src.dashboard.history_repository import ConditionHistoryRepository, create_history_repository_from_env


class OperationalIntelligenceRepository:
    def __init__(
        self,
        *,
        state_repository: DashboardRepository | None = None,
        history_repository: ConditionHistoryRepository | None = None,
    ) -> None:
        self.state_repository = state_repository or create_repository_from_env()
        self.history_repository = history_repository or create_history_repository_from_env()

    def get_current_state(self, tenant_id: str, asset_id: str) -> dict[str, Any]:
        return self.state_repository.get_latest_state(tenant_id=tenant_id, asset_id=asset_id) or {}

    def query_history(self, tenant_id: str, asset_id: str, hours: int = 24) -> list[dict[str, Any]]:
        end = datetime.now(UTC)
        start = end - timedelta(hours=hours)
        return self.history_repository.query_history(
            tenant_id=tenant_id,
            asset_id=asset_id,
            start_utc=start,
            end_utc=end,
        )
