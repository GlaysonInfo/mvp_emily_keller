"""
Referência de integração HMI para o app.py.

O app principal já aplica este padrão:

1. renderiza a sidebar HMI;
2. traduz o Modo Operador para as rotas existentes;
3. mantém o Modo Técnico com o menu completo;
4. finaliza cada página com st.stop().

Rotas do Modo Operador:

- Painel da Planta -> render_operator_home(...)
- Equipamento -> Detalhe do Ativo
- Lubrificação -> Sistema de Lubrificação
- Alertas -> Alertas e Eventos
- Relatórios -> Relatórios
- Ajuda -> render_operator_help()
"""
