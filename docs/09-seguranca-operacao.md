# Segurança e Operação

## 1. Princípios

A segurança do MVP deve ser simples, explícita e evolutiva.

O laboratório pode usar configurações facilitadas, desde que estejam claramente marcadas como não produtivas.

## 2. Segurança local

### 2.1 MQTT local

No laboratório, o Mosquitto pode permitir conexão anônima para reduzir fricção.

Exemplo de `mosquitto.conf` para laboratório:

```conf
listener 1883 0.0.0.0
allow_anonymous true
persistence false
log_type all
```

Aviso obrigatório:

```text
Esta configuração é apenas para laboratório. Não usar em produção.
```

### 2.2 OPC UA local

O servidor OPC UA local pode rodar sem autenticação no MVP.

Em produção ou fase 2, avaliar:

- Certificados.
- Segurança de canal.
- Usuário e senha.
- Lista de endpoints permitidos.

## 3. Segurança AWS

### 3.1 IAM

Cada componente deve ter permissões mínimas.

Lambda de ingestão deve acessar apenas:

- Bucket S3 do MVP.
- Tabela Timestream do MVP.
- Tabelas DynamoDB do MVP.
- EventBridge bus do MVP.
- CloudWatch Logs.

### 3.2 Segredos

Não gravar credenciais no código.

Usar:

- Variáveis de ambiente para configuração não sensível.
- AWS Secrets Manager ou Parameter Store para segredos futuros.
- Perfis IAM quando rodar em EC2.

### 3.3 Criptografia

Recomendado:

- S3 com criptografia ativada.
- DynamoDB com criptografia padrão.
- Timestream com criptografia gerenciada.
- HTTPS para API Gateway.
- MQTT com TLS no AWS IoT Core.

## 4. Logs

### 4.1 Logs locais

Cada serviço local deve registrar:

- Start/stop.
- Endpoint conectado.
- Erros de conexão.
- Mensagens publicadas.
- Cenário simulado atual.

### 4.2 Logs AWS

CloudWatch deve conter:

- Logs da Lambda normalizadora.
- Logs do motor de regras.
- Erros de validação.
- Falhas de gravação em S3/Timestream/DynamoDB.

## 5. Dados sensíveis

O MVP não deve coletar dados pessoais.

Campos permitidos:

- IDs técnicos de tenant, planta e ativo.
- Métricas do equipamento.
- Status de alerta.
- Recomendações técnicas.

Campos proibidos no MVP:

- Dados pessoais de operadores.
- Dados biométricos.
- Geolocalização individual de técnicos.
- Avaliação de produtividade individual.

## 6. Operação da demo

Antes da apresentação:

1. Testar simulador.
2. Testar UaExpert.
3. Testar broker MQTT.
4. Testar bridge.
5. Testar AWS.
6. Testar dashboard.
7. Ter fallback de vídeo ou prints caso a rede falhe.

Durante a apresentação:

1. Explicar escopo e restrições.
2. Mostrar OPC UA.
3. Mostrar dados em tempo real.
4. Mostrar detecção de falha.
5. Mostrar recomendação.
6. Explicar evolução para ambiente real.

Após a apresentação:

1. Desligar recursos locais.
2. Verificar custos AWS.
3. Registrar feedback do cliente.
4. Atualizar backlog.

## 7. Backup e recuperação

Para MVP:

- Código no Git.
- Configurações versionadas sem segredos.
- Dados brutos preservados no S3.
- Dashboard recriável por Docker.

## 8. Limitações declaradas

O MVP é demonstrativo e não deve ser usado para decisões críticas em ativos reais sem validação adicional.

Limitações:

- Dados simulados.
- Regras simplificadas.
- Sem calibração por máquina real.
- Sem integração com CMMS real.
- Sem certificado OPC UA no laboratório.
- Sem modelo de machine learning treinado com dados reais.

