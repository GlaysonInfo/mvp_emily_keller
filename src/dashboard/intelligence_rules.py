from __future__ import annotations

from typing import Any

try:
    from dashboard.intelligence_labels import metric_label
except ImportError:  # pragma: no cover - supports imports from repository root.
    from src.dashboard.intelligence_labels import metric_label


def classify_anomaly_level(score: float) -> str:
    if score >= 80:
        return "CRÍTICO"
    if score >= 55:
        return "ALERTA"
    if score >= 30:
        return "ATENÇÃO"
    return "NORMAL"


def explain_metric(metric: str, current: float | None, baseline_mean: float | None, deviation_pct: float | None, z_score: float, level: str) -> str:
    label = metric_label(metric)

    if current is None:
        return f"{label}: sem leitura atual suficiente para análise."

    if baseline_mean is None:
        return f"{label}: leitura atual disponível, mas ainda sem baseline histórico confiável."

    direction = "acima" if deviation_pct and deviation_pct > 0 else "abaixo"
    return (
        f"{label}: valor atual {current:.2f}, baseline {baseline_mean:.2f}, "
        f"desvio {direction} de {abs(deviation_pct or 0):.1f}% "
        f"(z-score {z_score:.2f}), nível {level}."
    )


def infer_failure_hypothesis(metric_results: list[dict[str, Any]], current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    current_state = current_state or {}
    by_metric = {item["metric"]: item for item in metric_results}

    def high(metric: str, min_score: float = 30) -> bool:
        return float(by_metric.get(metric, {}).get("score", 0) or 0) >= min_score

    def very_high(metric: str) -> bool:
        return high(metric, 55)

    mode = current_state.get("failure_mode_simulated") or current_state.get("mode") or ""
    status = current_state.get("status_label") or ""
    hypotheses: list[dict[str, Any]] = []

    if very_high("temperature_c") and not very_high("vibration_rms_mm_s"):
        hypotheses.append(
            {
                "hypothesis": "Aquecimento anormal",
                "confidence": 0.78,
                "evidence": [
                    "Temperatura desviou fortemente do baseline.",
                    "Vibração não acompanha a severidade térmica na mesma proporção.",
                    "Padrão compatível com sobrecarga, ventilação deficiente, sujeira, atrito ou condição elétrica.",
                ],
                "checks": [
                    "Verificar ventilação e obstrução por sujeira.",
                    "Medir corrente elétrica e comparar com placa do motor.",
                    "Verificar carga do processo.",
                    "Inspecionar rolamentos e condição de lubrificação.",
                ],
            }
        )

    if high("ultrasound_db") and (high("temperature_c") or high("vibration_rms_mm_s")):
        hypotheses.append(
            {
                "hypothesis": "Degradação de lubrificação",
                "confidence": 0.74,
                "evidence": [
                    "Ultrassom acima do padrão esperado.",
                    "Há reforço por temperatura ou vibração fora do baseline.",
                    "Padrão compatível com atrito, lubrificação insuficiente, contaminação ou aplicação inadequada.",
                ],
                "checks": [
                    "Confirmar última lubrificação e horímetro desde a intervenção.",
                    "Verificar tipo de lubrificante aplicado, lote, validade e compatibilidade.",
                    "Inspecionar contaminação cruzada, excesso ou falta de lubrificante.",
                    "Avaliar ruído e aquecimento nos mancais/rolamentos.",
                ],
            }
        )

    if high("kurtosis_index") or high("crest_factor_index") or very_high("vibration_peak_g"):
        hypotheses.append(
            {
                "hypothesis": "Falha inicial em rolamento ou eventos impulsivos",
                "confidence": 0.72,
                "evidence": [
                    "Kurtosis, Crest Factor ou Pico de vibração indicam eventos impulsivos.",
                    "Padrão compatível com impacto, defeito incipiente em rolamento, folga ou batimento.",
                ],
                "checks": [
                    "Inspecionar rolamentos, folgas, acoplamentos e fixação.",
                    "Realizar análise de vibração mais detalhada se disponível.",
                    "Verificar ruído, temperatura localizada e tendência de picos.",
                ],
            }
        )

    if very_high("vibration_rms_mm_s") and not very_high("temperature_c"):
        hypotheses.append(
            {
                "hypothesis": "Desbalanceamento, desalinhamento ou fixação inadequada",
                "confidence": 0.70,
                "evidence": [
                    "Vibração RMS elevada em relação ao baseline.",
                    "Temperatura não acompanha a severidade mecânica.",
                    "Padrão compatível com base, alinhamento, acoplamento ou balanceamento.",
                ],
                "checks": [
                    "Verificar base, parafusos e fixação.",
                    "Inspecionar acoplamento e alinhamento de eixo.",
                    "Avaliar balanceamento do conjunto.",
                    "Checar mudanças recentes no processo ou montagem.",
                ],
            }
        )

    if very_high("severity_score") or high("health_score", 55):
        hypotheses.append(
            {
                "hypothesis": "Risco operacional agregado",
                "confidence": 0.68,
                "evidence": [
                    "Health Score ou Severity Score indicam piora agregada.",
                    "O risco pode resultar da combinação de múltiplas variáveis, mesmo sem uma única métrica dominante.",
                ],
                "checks": [
                    "Priorizar inspeção no ativo.",
                    "Verificar variáveis que mais contribuíram para o score.",
                    "Registrar ação tomada na Central de Alertas.",
                ],
            }
        )

    if not hypotheses and mode:
        hypotheses.append(
            {
                "hypothesis": f"Condição operacional: {mode}",
                "confidence": 0.55,
                "evidence": [
                    f"O estado atual do ativo informa modo {mode}.",
                    f"Status operacional atual: {status}.",
                ],
                "checks": [
                    "Verificar histórico recente e confirmar se a condição persiste.",
                    "Comparar com parâmetros técnicos e baseline do ativo.",
                ],
            }
        )

    if not hypotheses:
        hypotheses.append(
            {
                "hypothesis": "Sem anomalia relevante detectada",
                "confidence": 0.60,
                "evidence": ["As variáveis atuais não apresentam desvio expressivo em relação ao baseline disponível."],
                "checks": ["Manter monitoramento e aguardar maior volume histórico."],
            }
        )

    hypotheses = sorted(hypotheses, key=lambda item: item["confidence"], reverse=True)
    return {"primary": hypotheses[0], "alternatives": hypotheses[1:]}


def build_ai_recommendation(metric_results: list[dict[str, Any]], current_state: dict[str, Any] | None = None) -> dict[str, Any]:
    hypothesis = infer_failure_hypothesis(metric_results, current_state)
    primary = hypothesis["primary"]

    return {
        "primary_hypothesis": primary["hypothesis"],
        "confidence": primary["confidence"],
        "evidence": primary["evidence"],
        "immediate_actions": list(primary.get("checks", [])),
        "preventive_actions": [
            "Registrar evidências no histórico do evento.",
            "Comparar a condição atual com o marco zero do ativo.",
            "Revisar periodicidade de manutenção/lubrificação se houver reincidência.",
            "Ajustar baseline após intervenção confirmada e retorno à condição saudável.",
        ],
        "risk_if_ignored": (
            "Se a condição persistir sem tratamento, há risco de progressão para alerta crítico, perda de eficiência, "
            "parada não programada e aumento do custo de manutenção."
        ),
        "alternatives": hypothesis.get("alternatives", []),
    }
