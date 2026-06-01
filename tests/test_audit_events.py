from __future__ import annotations

import json

from src.dashboard.audit_events import record_sensitive_action


def test_record_sensitive_action_writes_jsonl_fallback(monkeypatch, tmp_path) -> None:
    audit_file = tmp_path / "audit.log"
    monkeypatch.delenv("AUDIT_LOG_TABLE", raising=False)
    monkeypatch.setenv("AUDIT_LOG_FILE", str(audit_file))

    record_sensitive_action(
        "alert.update_status",
        target="alert-1",
        tenant_id="cliente_demo",
        details={"new_status": "acknowledged"},
    )

    event = json.loads(audit_file.read_text(encoding="utf-8").strip())

    assert event["action"] == "alert.update_status"
    assert event["target"] == "alert-1"
    assert event["tenant_id"] == "cliente_demo"
    assert event["details"] == {"new_status": "acknowledged"}
    assert event["source"] == "dashboard"
