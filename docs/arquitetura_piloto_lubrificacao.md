
# Arquitetura do Piloto — Lubrificação por Pressão

Cada manômetro físico representa uma saída de graxa. No piloto, os manômetros permanecem instalados e um sensor eletrônico de pressão é adicionado em paralelo.

```text
Saída de graxa
→ conexão em T
→ manômetro físico mantido
→ sensor de pressão 0–250 bar
→ gateway IO-Link
→ bridge edge
→ sistema em nuvem
→ dashboard / histórico / alertas / IA
```

## Componentes

| Item | Quantidade |
|---|---:|
| Sensores de pressão 0–250 bar | 4 |
| Conexões em T/adaptadores | 4 |
| Gateway IO-Link | 1 |
| Fonte 24 Vcc | 1 |
| Caixa elétrica | 1 |
| Bridge Edge | 1 |
| Tela no sistema | 1 |
