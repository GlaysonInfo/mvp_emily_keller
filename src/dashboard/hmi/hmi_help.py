from __future__ import annotations

import streamlit as st


def render_operator_help() -> None:
    st.header("Ajuda do Operador")
    st.caption("Guia rápido para interpretar o sistema no campo.")

    st.subheader("Cores e prioridades")
    st.markdown(
        """
| Situação | Significado | Ação |
|---|---|---|
| Normal | Operando dentro do esperado | Manter acompanhamento |
| Atenção | Desvio leve | Verificar na ronda |
| Alerta | Condição anormal relevante | Comunicar manutenção |
| Crítico | Risco alto de falha | Acionar responsável imediatamente |
"""
    )

    st.subheader("Quando aparecer alerta")
    st.markdown(
        """
1. Abrir **Alertas**.
2. Ver o equipamento ou saída com problema.
3. Ler a **ação recomendada**.
4. Confirmar evidência em campo.
5. Registrar a ação tomada.
6. Acionar manutenção quando necessário.
"""
    )

    st.subheader("Lubrificação")
    st.markdown(
        """
Baixa pressão pode indicar falta de graxa, vazamento, linha aberta ou pistão sem atuação.

Alta pressão ou alívio lento pode indicar obstrução, graxa endurecida, bico bloqueado ou ponto pesado.
"""
    )
