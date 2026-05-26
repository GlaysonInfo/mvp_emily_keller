from __future__ import annotations

from pathlib import Path

from scripts.validate_acceptance_config import load_acceptance_config


def test_acceptance_config_points_to_public_https_endpoint() -> None:
    config = load_acceptance_config()

    assert config["aws_region"] == "us-east-1"
    assert config["endpoint_health"] == "https://sentinelaindustrial.com.br/grease/health"
    assert config["endpoint_ingest"] == "https://sentinelaindustrial.com.br/grease/ingest"
    assert config["pilot_scope"]["physical_gauges_kept"] is True
    assert config["pilot_scope"]["sensor_range_bar"] >= 160


def test_acceptance_templates_are_present() -> None:
    expected_docs = [
        "docs/termo_aceite_piloto_lubrificacao.md",
        "docs/checklist_comissionamento_campo.md",
        "docs/relatorio_tecnico_piloto_lubrificacao.md",
        "docs/matriz_riscos_implantacao.md",
        "docs/plano_teste_campo_gateway_iolink.md",
        "docs/criterios_sucesso_piloto.md",
    ]

    missing = [path for path in expected_docs if not Path(path).exists()]

    assert missing == []
