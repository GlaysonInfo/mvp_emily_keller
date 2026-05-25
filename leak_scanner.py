from __future__ import annotations

import sys
from pathlib import Path


PATTERNS = [
    "render_plant_overview",
    "render_alerts_center",
    "render_notification_outbox_page",
    "render_escalation_page",
    "render_operational_intelligence_page",
    "Ativos por prioridade",
    "Eventos priorizados",
    "Tratamento do evento",
    "Alertas ativos",
]


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: python leak_scanner.py caminho/para/app.py")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Arquivo nao encontrado: {path}")
        return 1

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    print(f"Analisando: {path}")
    print("Ocorrencias suspeitas:")

    found = False
    for line_number, line in enumerate(lines, start=1):
        for pattern in PATTERNS:
            if pattern in line:
                found = True
                print(f"L{line_number:04d}: {line.strip()}")

    if not found:
        print("Nenhum padrao suspeito encontrado.")

    print("\nCada chamada acima deve estar dentro da rota correta e terminar com st.stop().")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
