from pathlib import Path


CONFIG = Path("deploy/auth/nginx_app_auth.conf")


def test_app_auth_signout_clears_cognito_session_before_returning_to_site() -> None:
    source = CONFIG.read_text(encoding="utf-8")

    assert "location = /oauth2/sign_out" in source
    assert "sentinela-industrial-login.auth.us-east-1.amazoncognito.com%2Flogout" in source
    assert "client_id%3D45541b6bo4hnj6ekhvj2htfp09" in source
    assert "logout_uri%3Dhttps%253A%252F%252Fsentinelaindustrial.com.br%252F" in source


def test_oauth2_auth_endpoint_is_internal_only() -> None:
    source = CONFIG.read_text(encoding="utf-8")

    assert "location = /oauth2/auth" in source
    assert "internal;" in source
