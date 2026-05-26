# Segurança do Endpoint

Recomendações:
- ativar `GREASE_INGEST_TOKEN`;
- enviar `X-API-Key`;
- restringir Security Group para IP do gateway;
- opcionalmente usar `GREASE_ALLOWED_SOURCE_IPS`.

Variáveis:

```text
GREASE_INGEST_TOKEN=token_do_piloto
GREASE_ALLOWED_SOURCE_IPS=ip_gateway,ip_tecnico
```
