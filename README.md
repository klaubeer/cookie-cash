# Cookie Finance Bot

![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat&logo=docker&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?style=flat&logo=openai&logoColor=white)
![Google Sheets](https://img.shields.io/badge/Google_Sheets-API_v4-34A853?style=flat&logo=googlesheets&logoColor=white)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Evolution_API_v2-25D366?style=flat&logo=whatsapp&logoColor=white)

Bot de controle financeiro para negócio de cookies artesanais, operado inteiramente via WhatsApp. A usuária envia fotos de recibos, mensagens de texto ou áudios com vendas e despesas; uma IA extrai as informações e registra tudo em uma planilha Google Sheets com saldo em tempo real.

## Por que esse projeto existe

Pequenos negócios artesanais raramente têm um processo de controle financeiro estruturado. O dia a dia é corrido — produção, vendas, compras de insumos — e registrar cada movimentação em uma planilha exige disciplina, tempo e uma mudança de contexto que a maioria das pessoas simplesmente não faz.

O resultado é previsível: no fim do mês, não se sabe com precisão quanto entrou, quanto saiu e se o negócio deu lucro de verdade.

O Cookie Finance Bot resolve isso eliminando a fricção do registro. A usuária já usa o WhatsApp o dia inteiro; agora basta mandar uma mensagem como faria normalmente — "Joana levou 4 cookies, R$60", um áudio no trânsito ou a foto do recibo do mercado — e o bot cuida do resto. Nenhum app novo para aprender, nenhum formulário para preencher, nenhum dado perdido porque "vou lançar depois".

O controle financeiro passa a acontecer de forma natural, no mesmo lugar onde o negócio já acontece.

---

## Como funciona

```
[WhatsApp]
    │  Foto de recibo / texto / áudio
    ▼
[Evolution API]  →  POST webhook
    ▼
[FastAPI — webhook/router.py]
    │  Valida → enfileira → responde 200 imediatamente
    ▼
[Worker assíncrono — asyncio.Queue]
    │
    ├─ É resposta de confirmação pendente?
    │       └─ Resolve pendência → salva no Sheets → confirma no WhatsApp
    │
    ├─ Texto ou áudio
    │       ├─ Áudio → Whisper API → texto transcrito
    │       └─ GPT-4o mini → classifica (RECEITA / DESPESA / IGNORAR)
    │               ├─ IGNORAR → encerra sem resposta
    │               └─ RECEITA / DESPESA
    │                       ├─ confiança ≥ 0.85 → salva direto → confirma
    │                       └─ confiança < 0.85 → pede confirmação → aguarda sim/não
    │
    └─ Imagem (recibo)
            └─ GPT-4o mini Vision → extrai estabelecimento, valor, data
                    └─ mesmo fluxo de confiança acima
```

---

## Features

- **Registro por foto** — envia o recibo do mercado e o bot extrai estabelecimento, valor e data automaticamente
- **Registro por texto livre** — sem formato fixo: "Joana levou 4 cookies, R$60" é suficiente
- **Registro por áudio** — mensagens de voz são transcritas via Whisper e processadas como texto
- **Confirmação inteligente** — quando a confiança da extração é baixa, o bot pede confirmação antes de salvar
- **Comando `/resumo`** — retorna receitas, despesas e saldo do mês diretamente no WhatsApp
- **Google Sheets em tempo real** — cada lançamento gera uma nova linha na aba "Lançamentos"
- **Dashboard de resumo** — aba "Resumo" com seletor de período, totais e saldo calculados por fórmulas
- **Filtro por chat** — processa apenas o grupo ou conversa configurada, ignora todo o resto
- **Mensagens não financeiras ignoradas em silêncio** — lembretes, conversas gerais e figurinhas não geram nenhuma resposta

---

## Stack tecnológica

| Componente | Tecnologia | Versão |
|---|---|---|
| WhatsApp | Evolution API (self-hosted) | v2 |
| Backend | Python + FastAPI | 3.12 / 0.115.x |
| Servidor ASGI | Uvicorn | 0.30.x |
| Validação | Pydantic v2 | 2.7.x |
| LLM + Visão | OpenAI GPT-4o mini | — |
| Transcrição de áudio | OpenAI Whisper API | — |
| Planilha | Google Sheets API v4 | — |
| Autenticação Google | google-auth (service account) | 2.x |
| HTTP client | httpx | 0.27.x |
| Configuração | pydantic-settings | 2.x |
| Containerização | Docker + Compose | 27.x / 2.x |

---

## Estrutura de pastas

```
cookie-cash/
├── PRD.md                       # Requisitos do produto
├── SDD.md                       # Design do software (ADRs, arquitetura)
├── CONTEXT.md                   # Estado atual do projeto (atualizado por sessão)
├── docker-compose.yml
├── .env.example
│
└── app/
    ├── main.py                  # Entrypoint FastAPI — lifespan, rotas, worker
    ├── config.py                # Lê variáveis de ambiente via pydantic-settings
    │
    ├── webhook/
    │   ├── router.py            # POST /webhook — recebe eventos da Evolution API
    │   └── schema.py            # Modelos Pydantic dos payloads da Evolution API
    │
    ├── processador/
    │   ├── dispatcher.py        # Roteia mensagem para o handler correto
    │   ├── extrator.py          # Monta prompts e chama GPT-4o mini
    │   ├── confirmacao.py       # Gerencia confirmações pendentes (dict com TTL)
    │   └── schema.py            # Modelos: Transacao, TipoTransacao
    │
    ├── integracoes/
    │   ├── whatsapp.py          # Envia mensagens e baixa mídia via Evolution API
    │   ├── sheets.py            # Append de linhas e leitura de resumo no Sheets
    │   └── audio.py             # Transcrição de áudio via Whisper
    │
    └── utils/
        ├── fila.py              # asyncio.Queue — serializa writes no Sheets
        └── logging.py           # Logs estruturados em JSON
```

---

## Configuração e execução

### Pré-requisitos

- Docker e Docker Compose instalados na VPS
- Conta de serviço Google com acesso à planilha (`.json` exportado do Google Cloud Console)
- Instância da Evolution API rodando (pode ser separada)
- Chave de API da OpenAI

### 1. Clone e configure o ambiente

```bash
git clone <repo>
cd cookie-cash
cp .env.example .env
```

Edite o `.env` com os valores reais (veja a seção de variáveis de ambiente abaixo).

### 2. Configure o webhook na Evolution API

Aponte o webhook da sua instância Evolution para:

```
http://<ip-da-vps>:8000/webhook
```

Evento necessário: `MESSAGES_UPSERT`

### 3. Suba os containers

```bash
docker compose up -d
```

O bot inicializa a aba "Resumo" do Google Sheets automaticamente na primeira execução.

### 4. Verifique o health check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

---

## Variáveis de ambiente

Copie `.env.example` para `.env` e preencha cada variável:

```env
# ── Evolution API (WhatsApp) ─────────────────────────────────────────────────
EVOLUTION_API_URL=http://evolution:8080
EVOLUTION_API_KEY=sua_chave_aqui
EVOLUTION_INSTANCE=cookie-bot

# ── OpenAI (GPT-4o mini + Whisper) ──────────────────────────────────────────
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# ── Google Sheets ────────────────────────────────────────────────────────────
# ID da planilha (encontrado na URL: /spreadsheets/d/<ID>/edit)
GOOGLE_SHEETS_ID=id_da_planilha_aqui

# JSON completo da service account em uma única linha (sem quebras de linha)
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}

# ── WhatsApp ─────────────────────────────────────────────────────────────────
# ID do grupo ou chat monitorado pelo bot
# Formato grupo:  120363XXXXXXXXX@g.us
# Formato direto: 5511999999999@s.whatsapp.net
GRUPO_WHATSAPP_ID=120363XXXXXXXXX@g.us

# ── App ──────────────────────────────────────────────────────────────────────
LOG_LEVEL=INFO
CONFIRMACAO_TTL_SEGUNDOS=300
CONFIANCA_MIN=0.85
```

---

## Arquitetura resumida

O bot é uma aplicação **FastAPI** de processo único com dois componentes principais rodando de forma concorrente:

**Webhook (síncrono na borda):** recebe o `POST /webhook` da Evolution API, valida o payload, enfileira a mensagem em uma `asyncio.Queue` e retorna `200 OK` imediatamente — sem bloquear o caller.

**Worker assíncrono (processamento real):** consome a fila continuamente. Para cada mensagem, identifica o tipo de mídia (texto, áudio ou imagem), chama os serviços externos necessários (Whisper para áudio, GPT-4o mini para extração e classificação), gerencia o estado de confirmações pendentes em memória e escreve na planilha via Google Sheets API.

A serialização de writes via fila elimina race conditions no Sheets sem precisar de um banco de dados adicional. O estado de confirmações pendentes é mantido em um dicionário em memória com TTL de 5 minutos — reiniciar o container descarta confirmações em aberto, o que é aceitável dado o tempo curto de expiração.

### Planilha Google Sheets

A planilha tem duas abas:

- **Lançamentos** — uma linha por transação com colunas: Data, Tipo, Descrição, Valor (R$), Origem e Timestamp. Escrita via API a cada novo lançamento.
- **Resumo** — configurada automaticamente na inicialização com fórmulas `SUMPRODUCT`, dropdown de período (a partir de 03/2026) e totais gerais sem filtro. Nenhuma escrita via API após a configuração inicial.

### Segurança

| Superfície | Mitigação |
|---|---|
| Webhook público | Filtro por `chat_id` — ignora qualquer mensagem fora do grupo configurado |
| Credenciais Google | Armazenadas como variável de ambiente, nunca versionadas |
| Chave OpenAI | Idem — `.env` fora do controle de versão |
| Injeção via mensagem | Prompt isolado com instrução explícita de retornar apenas JSON estruturado |

---

## Licença

Uso privado.
