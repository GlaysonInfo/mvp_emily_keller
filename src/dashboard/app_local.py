from __future__ import annotations

import os
import sys


def _streamlit_port_from_args() -> str | None:
    for index, arg in enumerate(sys.argv):
        if arg == "--server.port" and index + 1 < len(sys.argv):
            return sys.argv[index + 1]
        if arg.startswith("--server.port="):
            return arg.split("=", 1)[1]
    return None


# Local preview entrypoint: force the dashboard to use bundled demo JSON files
# instead of DynamoDB, regardless of broken AWS credentials in the shell.
os.environ["DASHBOARD_DATA_MODE"] = "local"
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
    os.environ.pop(name, None)

_LOCAL_AUTH_IDENTITIES = {
    "8502": '{"email":"op@cliente.com","groups":["CLIENTE_OPERADOR","TENANT_cliente_demo"],"services":["condition","lubrication"]}',
    "8503": '{"email":"tec@cliente.com","groups":["CLIENTE_TECNICO","TENANT_cliente_demo"],"services":["condition","lubrication"]}',
    "8504": '{"email":"admin@sentinela.com","groups":["ADMIN_SERVER"],"services":["condition","lubrication"]}',
    "8505": '{"email":"admin@cliente.com","groups":["CLIENTE_ADMIN","TENANT_cliente_demo"],"services":["condition","lubrication"]}',
}

_port = _streamlit_port_from_args()
if _port in _LOCAL_AUTH_IDENTITIES:
    os.environ["AUTH_ENABLED"] = "true"
    os.environ["AUTH_DEV_IDENTITY"] = _LOCAL_AUTH_IDENTITIES[_port]
    os.environ.setdefault("INSTITUTIONAL_SITE_URL", "http://127.0.0.1:8081/")

try:
    from dashboard.app import main
except ImportError:  # pragma: no cover - supports streamlit run from repository root.
    from src.dashboard.app import main


main()
