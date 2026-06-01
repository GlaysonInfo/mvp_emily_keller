# Vitrine institucional - Sentinela Industrial

Site estatico (HTML/CSS) para `https://sentinelaindustrial.com.br/`, separado
da aplicacao operacional em `app.sentinelaindustrial.com.br`, atras de login.
A estrutura segue o relatorio de pesquisa do projeto e preserva a area
operacional como uma experiencia autenticada independente da vitrine publica.

## Paginas publicadas neste pacote

| Pagina | Caminho | Indexacao |
|---|---|---|
| Home | `index.html` | index |
| Produto (Sistema de Lubrificacao) | `sistema-de-lubrificacao/index.html` | index |
| Como funciona | `como-funciona/index.html` | index |
| Demonstracao (lead) | `demonstracao/index.html` | index |
| Contato | `contato/index.html` | index |
| Privacidade | `privacidade/index.html` | index |
| Cookies | `cookies/index.html` | index |
| Termos | `termos/index.html` | index |
| Acesso ao Sistema (hub) | `acesso/index.html` | **noindex** |

## Paginas a criar a seguir

`configuracao-de-campo/`, `hmi-de-campo/`, `casos-de-uso/`, `ofertas/`,
`blog/`, `base-de-conhecimento/`. Ao publicar cada uma, adicione a URL ao
`sitemap.xml`.

### Padrao editorial (title / meta description)

| Pagina | Title | Meta description |
|---|---|---|
| Home | Sentinela Industrial \| Monitoramento de Lubrificacao e Condicao | MVP de monitoramento de lubrificacao com gateway, nuvem, diagnostico e HMI de campo para operador e tecnico. |
| Produto | Sistema de Lubrificacao \| Monitoramento por pressao de saida | Detecte baixa pressao, alta pressao e alivio lento por saida de graxa com diagnostico e acoes recomendadas. |
| Demonstracao | Demonstracao \| Sistema de Lubrificacao | Agende uma demonstracao e veja o fluxo gateway -> API -> AWS -> HMI. |
| Contato | Contato \| Sentinela Industrial | Fale com a Sentinela Industrial sobre pilotos, demonstracoes e duvidas comerciais ou tecnicas. |
| Privacidade | Privacidade \| Sentinela Industrial | Como tratamos dados pessoais em formularios, acesso demonstrativo e operacao da plataforma. |
| Cookies | Cookies \| Sentinela Industrial | Uso de cookies essenciais e analiticos no site e no acesso demonstrativo. |
| Termos | Termos \| Sentinela Industrial | Termos de uso do site e do acesso demonstrativo da Sentinela Industrial. |
| Blog | Blog \| Sentinela Industrial | Conteudo tecnico sobre lubrificacao, monitoramento, sensores e implantacao. |

### Dados estruturados (JSON-LD) por pagina

| Pagina | Schema |
|---|---|
| Home | `Organization`, `WebSite` |
| Produto | `SoftwareApplication`, `BreadcrumbList` |
| FAQ / base de conhecimento | `FAQPage`, `BreadcrumbList` |
| Blog post | `Article` |
| Contato | `Organization` com `contactPoint` |

## Conteudo a reaproveitar

Materiais ja existentes em `Arquivos de Apoio e Implementacao/` viram artigos e
iscas de captura: e-book de indicadores de manutencao, e-book de monitoramento e
analise de vibracao, material de salas de lubrificacao. Palavras-chave iniciais:
lubrificacao centralizada, monitoramento de pressao de graxa, lubrificacao por
saida, gateway IO-Link lubrificacao, manutencao baseada em condicao.

## Pendencias de integracao

- `demonstracao/index.html`: ligar o `action` do formulario ao CRM
  (HubSpot/RD Station) ou a um webhook.
- `contato/index.html`: trocar o link `mailto:` por CRM/webhook quando o canal
  oficial estiver definido.
- `index.html`: inserir o ID real do **GA4** (bloco comentado) e validar o
  dominio no **Google Search Console**.
- Botoes de "Entrar" em `acesso/` apontam para `app.sentinelaindustrial.com.br`
  em producao e para o Streamlit local quando a pagina roda em localhost.
- Em localhost, `acesso/` tambem mostra perfis simulados: Operador (`8502`),
  Tecnico (`8503`), Cliente Admin (`8505`) e Admin do Sistema (`8504`).

## Deploy (S3 + CloudFront)

```bash
# Bucket privado servido via CloudFront (OAC). Certificado ACM em us-east-1.
aws s3 sync . s3://SEU-BUCKET-DO-SITE/ --delete \
  --exclude "README.md"
# Invalidar cache apos o deploy:
aws cloudfront create-invalidation --distribution-id SUA_DIST --paths "/*"
```

Configure no CloudFront: indice padrao `index.html`, HTTPS obrigatorio e,
quando evoluir, AWS WAF com regra de taxa.
