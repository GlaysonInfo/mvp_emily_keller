from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.contact_api import app
from src.api.contact_models import ContactSubmission
from src.api.contact_service import reset_rate_limits, send_contact_email


def _payload() -> dict:
    return {
        "contact_type": "Demonstração",
        "name": "Maria Industrial",
        "email": "maria@empresa.com.br",
        "company": "Empresa Teste",
        "phone": "+55 31 99999-0000",
        "subject": "",
        "message": "Quero avaliar dois motores e uma esteira.",
        "consent": True,
        "website": "",
    }


class FakeSesClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def send_email(self, **kwargs) -> dict:
        self.requests.append(kwargs)
        return {"MessageId": "ses-message-001"}


def test_contact_health_reports_delivery_configuration(monkeypatch) -> None:
    monkeypatch.setenv("CONTACT_FROM_EMAIL", "suporte@meuprompt.net")
    monkeypatch.setenv("CONTACT_TO_EMAIL", "suporte@meuprompt.net")

    response = TestClient(app).get("/contact/health")

    assert response.status_code == 200
    assert response.json()["service"] == "contact-api"
    assert response.json()["delivery_configured"] is True


def test_contact_submit_delivers_inside_api(monkeypatch) -> None:
    reset_rate_limits()
    monkeypatch.setattr("src.api.contact_api.send_contact_email", lambda payload, client_ip: "request-123")

    response = TestClient(app).post(
        "/contact/submit",
        headers={"Origin": "https://sentinelaindustrial.com.br", "X-Real-IP": "198.51.100.10"},
        json=_payload(),
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["request_id"] == "request-123"


def test_contact_submit_rejects_untrusted_origin() -> None:
    reset_rate_limits()

    response = TestClient(app).post(
        "/contact/submit",
        headers={"Origin": "https://example.invalid"},
        json=_payload(),
    )

    assert response.status_code == 403


def test_contact_submit_requires_privacy_consent() -> None:
    reset_rate_limits()
    payload = _payload()
    payload["consent"] = False

    response = TestClient(app).post("/contact/submit", json=payload)

    assert response.status_code == 422


def test_contact_honeypot_returns_success_without_delivery(monkeypatch) -> None:
    reset_rate_limits()
    calls: list[object] = []
    monkeypatch.setattr(
        "src.api.contact_api.send_contact_email",
        lambda payload, client_ip: calls.append((payload, client_ip)),
    )
    payload = _payload()
    payload["website"] = "https://spam.invalid"

    response = TestClient(app).post("/contact/submit", json=payload)

    assert response.status_code == 200
    assert response.json()["request_id"] == "accepted"
    assert calls == []


def test_contact_rate_limit_blocks_excess_requests(monkeypatch) -> None:
    reset_rate_limits()
    monkeypatch.setenv("CONTACT_RATE_LIMIT", "1")
    monkeypatch.setenv("CONTACT_RATE_WINDOW_SECONDS", "900")
    monkeypatch.setattr("src.api.contact_api.send_contact_email", lambda payload, client_ip: "request-123")
    client = TestClient(app)
    headers = {"X-Real-IP": "198.51.100.20"}

    first = client.post("/contact/submit", headers=headers, json=_payload())
    second = client.post("/contact/submit", headers=headers, json=_payload())

    assert first.status_code == 200
    assert second.status_code == 429


def test_send_contact_email_uses_ses_and_reply_to(monkeypatch) -> None:
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("CONTACT_FROM_EMAIL", "suporte@meuprompt.net")
    monkeypatch.setenv("CONTACT_TO_EMAIL", "suporte@meuprompt.net")
    fake_ses = FakeSesClient()

    request_id = send_contact_email(
        ContactSubmission(**_payload()),
        client_ip="198.51.100.30",
        ses_client=fake_ses,
    )

    assert len(request_id) == 32
    assert fake_ses.requests[0]["Source"] == "suporte@meuprompt.net"
    assert fake_ses.requests[0]["Destination"]["ToAddresses"] == ["suporte@meuprompt.net"]
    assert fake_ses.requests[0]["ReplyToAddresses"] == ["maria@empresa.com.br"]
    assert "Empresa Teste" in fake_ses.requests[0]["Message"]["Subject"]["Data"]


def test_send_contact_email_removes_header_line_breaks(monkeypatch) -> None:
    monkeypatch.setenv("CONTACT_FROM_EMAIL", "suporte@meuprompt.net")
    monkeypatch.setenv("CONTACT_TO_EMAIL", "suporte@meuprompt.net")
    fake_ses = FakeSesClient()
    payload = _payload()
    payload["subject"] = "Demonstração\r\nBcc: terceiro@example.com"

    send_contact_email(
        ContactSubmission(**payload),
        client_ip="198.51.100.31",
        ses_client=fake_ses,
    )

    subject = fake_ses.requests[0]["Message"]["Subject"]["Data"]
    assert "\r" not in subject
    assert "\n" not in subject


def test_send_contact_email_requires_verified_sender_configuration(monkeypatch) -> None:
    monkeypatch.delenv("CONTACT_FROM_EMAIL", raising=False)
    monkeypatch.setenv("CONTACT_TO_EMAIL", "suporte@meuprompt.net")

    try:
        send_contact_email(
            ContactSubmission(**_payload()),
            client_ip="198.51.100.40",
            ses_client=FakeSesClient(),
        )
    except RuntimeError as exc:
        assert "remetente" in str(exc)
    else:
        raise AssertionError("Expected missing sender configuration to fail.")
