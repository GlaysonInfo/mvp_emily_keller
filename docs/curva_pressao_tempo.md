# Curva Pressão x Tempo

A curva por saída permite identificar:
- pulso normal;
- baixa pressão;
- sobrepressão;
- alívio lento;
- ausência de pulso.

Formato de amostra:

```json
{"ts_ms": 200, "pressure_bar": 15.2}
```

A bridge converte a curva em:
- pico;
- média;
- mínimo;
- tempo de subida;
- tempo de alívio.
