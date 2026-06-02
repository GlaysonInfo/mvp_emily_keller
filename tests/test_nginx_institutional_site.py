from pathlib import Path


CONFIG = Path("deploy/nginx_institutional_site.conf")


def test_institutional_site_serves_static_site_not_streamlit_root() -> None:
    source = CONFIG.read_text(encoding="utf-8")

    assert "server_name sentinelaindustrial.com.br www.sentinelaindustrial.com.br;" in source
    assert "root /opt/automacaoapi/site;" in source
    assert "try_files $uri $uri/ /index.html;" in source
    assert "proxy_pass http://127.0.0.1:8501" not in source


def test_institutional_site_redirects_oauth_paths_to_app_subdomain() -> None:
    source = CONFIG.read_text(encoding="utf-8")

    assert "location ^~ /oauth2/" in source
    assert "return 302 https://app.sentinelaindustrial.com.br$request_uri;" in source
