
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone

def load_json(path: str):
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))

def load_csv_text(path: str):
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8-sig")


def load_acceptance_config():
    configured = Path(os.getenv("ACCEPTANCE_CONFIG", "config/acceptance_config.json"))
    if configured.exists():
        return load_json(str(configured))
    return load_json("config/acceptance_config.example.json")


def main():
    config = load_acceptance_config()
    bom = load_csv_text("config/bom_piloto_lubrificacao.csv")
    checklist = load_csv_text("config/checklist_comissionamento_campo.csv")
    risks = load_csv_text("config/matriz_riscos_implantacao.csv")

    out = Path("reports/acceptance")
    out.mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    report = []
    report.append("# RELATÓRIO DE ACEITE DO PILOTO — LUBRIFICAÇÃO POR PRESSÃO")
    report.append("")
    report.append(f"Gerado em: {generated_at}")
    report.append("")
    report.append("## 1. Identificação")
    report.append("")
    report.append(f"Projeto: {config.get('project', '-')}")
    report.append(f"Região AWS: {config.get('aws_region', '-')}")
    report.append(f"EC2: {config.get('ec2_host', '-')}")
    report.append(f"Endpoint ingestão: {config.get('endpoint_ingest', '-')}")
    report.append("")
    report.append("## 2. Escopo do piloto")
    report.append("")
    scope = config.get("pilot_scope", {})
    for key, value in scope.items():
        report.append(f"- {key}: {value}")
    report.append("")
    report.append("## 3. Critérios de aceite")
    report.append("")
    for item in config.get("acceptance_criteria", []):
        report.append(f"- [ ] {item}")
    report.append("")
    report.append("## 4. Lista técnica de materiais")
    report.append("")
    report.append("```csv")
    report.append(bom.strip())
    report.append("```")
    report.append("")
    report.append("## 5. Checklist de comissionamento")
    report.append("")
    report.append("```csv")
    report.append(checklist.strip())
    report.append("```")
    report.append("")
    report.append("## 6. Matriz de riscos")
    report.append("")
    report.append("```csv")
    report.append(risks.strip())
    report.append("```")
    report.append("")
    report.append("## 7. Conclusão")
    report.append("")
    report.append("[ ] Piloto aprovado")
    report.append("[ ] Piloto aprovado com pendências")
    report.append("[ ] Piloto não aprovado nesta etapa")
    report.append("")

    md_path = out / "relatorio_aceite_piloto_lubrificacao.md"
    txt_path = out / "relatorio_aceite_piloto_lubrificacao.txt"

    md_path.write_text("\n".join(report), encoding="utf-8")
    txt_path.write_text("\n".join(report), encoding="utf-8")

    print(f"Relatórios gerados:")
    print(md_path)
    print(txt_path)

if __name__ == "__main__":
    main()
