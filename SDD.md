# SDD — Cookie Finance Bot

> Versão 1.0 — 27/03/2026

---

## 1. Decisões Arquiteturais (ADRs)

### ADR-01 — Webhook como ponto de entrada (vs. polling)

**Contexto:** A Evolution API suporta tanto polling quanto webhook para receber mensagens.

**Decisão:** Webhook HTTP POST para o FastAPI.

**Alternativas descartadas:**
- Polling periódico — introduz latência artificial e consumo desnecessário de CPU.

**Consequências:** A VPS precisa ter porta exposta (ou ngrok em dev). O FastAPI deve responder em < 5 s para evitar retentativas da Evolution API.

---

### ADR-02 — GPT-4o mini para OCR + NLP (vs. Claude Haiku)

**Contexto:** Precisamos extrair dados de imagens e texto livre. Áudio sempre exige serviço separado (Whisper) independente do LLM escolhido.

**Decisão:** GPT-4o mini via OpenAI API. Suporta visão + texto. Custo ~6,5× menor que Haiku no input e ~8× no output ($0,15/$0,60 vs $1,00/$5,00 por M tokens).

**Alternativas descartadas:**
- Claude Haiku 4.5 — mesmo conjunto de funcionalidades a custo significativamente maior.
- GPT-4.1 mini — intermediário em custo sem ganho relevante para extração simples.
- Tesseract OCR + spaCy — frágil para texto informal, sem suporte a linguagem natural.

**Consequências:** Dependência da OpenAI API. Estimativa de custo < R$20/mês mantida.

---

### ADR-03 — Google Sheets como banco de dados (vs. PostgreSQL)

**Contexto:** O marido acompanha os números diretamente na planilha.

**Decisão:** Google Sheets é tanto o storage quanto o dashboard. Sem banco relacional separado.

**Alternativas descartadas:**
- PostgreSQL + Metabase — complexidade desnecessária para volume de dados esperado (< 500 linhas/mês).
- SQLite — não acessível pelo usuário sem interface.

**Consequências:** Sem transações ACID. Risco de race condition se duas mensagens chegarem simultaneamente → mitigado com fila em memória (asyncio.Queue).

---

### ADR-04 — Sem persistência de estado entre mensagens (vs. banco de sessões)

**Contexto:** CU-04 exige confirmação antes de salvar (pergunta/resposta).

**Decisão:** Estado de confirmação pendente armazenado em dicionário em memória (`dict[chat_id → PendingEntry]`), com TTL de 5 minutos.

**Alternativas descartadas:**
- Redis — overhead de infra para um único usuário.
- Banco SQLite para sessões — mesmo problema menor.

**Consequências:** Reiniciar o container descarta confirmações pendentes. Aceitável dado o TTL curto.

---

## 2. Estrutura de Pastas e Módulos

```
cookie-cash/
├── PRD.md
├── SDD.md
├── CONTEXT.md
├── docker-compose.yml
├── .env.example
│
└── app/
    ├── main.py                  # Entrypoint FastAPI, registra rotas
    ├── config.py                # Lê .env via pydantic-settings
    │
    ├── webhook/
    │   ├── router.py            # POST /webhook — recebe eventos da Evolution API
    │   └── schema.py            # Pydantic models dos payloads da Evolution API
    │
    ├── processador/
    │   ├── dispatcher.py        # Roteia mensagem para handler correto (imagem/texto/áudio)
    │   ├── extrator.py          # Monta prompts e chama Claude API
    │   ├── confirmacao.py       # Gerencia estado de confirmação pendente (TTL dict)
    │   └── schema.py            # Pydantic models: Transacao, TipoTransacao, etc.
    │
    ├── integrações/
    │   ├── whatsapp.py          # Envia mensagens via Evolution API
    │   ├── sheets.py            # Append / leitura de linhas no Google Sheets
    │   └── audio.py             # Transcrição de áudio (Whisper via OpenAI API)
    │
    └── utils/
        ├── fila.py              # asyncio.Queue para serializar writes no Sheets
        └── logging.py           # Configuração de logs estruturados (JSON)
```

**Responsabilidade de cada módulo:**

| Módulo | Responsabilidade |
|--------|-----------------|
| `webhook/router.py` | Validar assinatura, enfileirar mensagem, responder 200 imediatamente |
| `processador/dispatcher.py` | Identificar tipo de mídia e delegar ao handler adequado |
| `processador/extrator.py` | Construir prompt contextual, chamar GPT-4o mini, parsear resposta |
| `processador/confirmacao.py` | Armazenar e recuperar entradas pendentes por `chat_id` |
| `integrações/sheets.py` | Abstrair Google Sheets API (append, batch_get para resumo) |
| `integrações/whatsapp.py` | Abstrair Evolution API (send_text, download_media) |
| `utils/fila.py` | Garantir que apenas um worker escreve no Sheets por vez |

---

## 3. Stack e Versões Fixadas

| Componente | Tecnologia | Versão |
|---|---|---|
| Runtime | Python | 3.12 |
| Web framework | FastAPI | 0.115.x |
| Servidor ASGI | Uvicorn | 0.30.x |
| Validação | Pydantic v2 | 2.7.x |
| LLM | openai SDK | 1.x |
| Sheets | google-api-python-client | 2.x |
| Auth Google | google-auth | 2.x |
| HTTP client | httpx | 0.27.x |
| Variáveis de ambiente | pydantic-settings | 2.x |
| Containerização | Docker + Compose | 27.x / 2.x |

---

## 4. Fluxo de Mensagens

```
[WhatsApp]
    │  POST evento
    ▼
[webhook/router.py]
    │  valida → enfileira → retorna 200
    ▼
[utils/fila.py — worker assíncrono]
    │
    ├─ tipo == CONFIRMACAO_RESPOSTA?
    │       └─ confirmacao.py → resolve pendência → sheets.py → whatsapp.py
    │
    ├─ tipo == TEXTO ou ÁUDIO
    │       ├─ áudio? → integrações/audio.py (Whisper) → texto transcrito
    │       └─ extrator.py (Claude) → classifica
    │               ├─ tipo == IGNORAR → encerra (sem resposta)
    │               └─ tipo == RECEITA/DESPESA → confirmacao.py → [aguarda sim/não]
    │                                                            ou salva direto
    │
    └─ tipo == IMAGEM
            └─ extrator.py (Claude vision) → classifica
                    ├─ tipo == IGNORAR → encerra (sem resposta)
                    └─ tipo == DESPESA → confirmacao.py → [aguarda] ou salva direto
```

**Regra de confirmação:** Se `confiança < 0.85` (campo retornado pelo LLM), o bot pede confirmação. Acima disso, salva direto e confirma no chat.

---

## 5. Estrutura da Planilha Google Sheets

### Aba — Lançamentos

| Coluna | Campo | Exemplo |
|--------|-------|---------|
| A | Data | 27/03/2026 |
| B | Tipo | RECEITA / DESPESA |
| C | Descrição | Joana — 4 cookies |
| D | Valor (R$) | 60,00 |
| E | Origem | texto / foto / áudio |
| F | Timestamp | 2026-03-27T14:32:00 |

### Aba — Resumo

Alimentada por fórmulas na própria planilha, sem escrita via API. Contém um seletor de período que controla todos os cálculos.

**Seletor de período (célula B2 — dropdown via Data Validation):**

| Opção | De | Até |
|---|---|---|
| Mês atual | 1º dia do mês corrente | Último dia do mês corrente |
| Ano atual | 01/01/ano corrente | 31/12/ano corrente |
| Últimos 7 dias | HOJE()-7 | HOJE() |
| Últimos 30 dias | HOJE()-30 | HOJE() |
| Personalizado | usuária digita em B4 | usuária digita em C4 |

Células B3 e C3 calculam De/Até automaticamente com `IFS` baseado na seleção. No modo "Personalizado", B3/C3 espelham B4/C4.

**Fórmulas de totais** usam `SUMPRODUCT` filtrando `Lançamentos!A:A >= De` e `<= Até`:

```
Receitas  =SUMPRODUCT((Lançamentos!A2:A1000>=B3)*(Lançamentos!A2:A1000<=C3)*(Lançamentos!B2:B1000="RECEITA")*Lançamentos!D2:D1000)
Despesas  =SUMPRODUCT(... "DESPESA" ...)
Saldo     = Receitas - Despesas
```

---

## 6. Contrato dos Prompts LLM

### Prompt — Extração de texto/áudio

```
Você é um assistente financeiro. Analise a mensagem abaixo.

Mensagem: "{mensagem}"
Data atual: {data_hoje}

Primeiro, classifique a mensagem em uma das categorias:
- RECEITA: dinheiro recebido por venda realizada
- DESPESA: dinheiro gasto em compra já realizada
- IGNORAR: qualquer outra coisa (lembrete, intenção futura, conversa, link, etc.)

Se RECEITA ou DESPESA, retorne:
{
  "tipo": "RECEITA" | "DESPESA",
  "descricao": "string curta",
  "valor": número float,
  "data": "YYYY-MM-DD",
  "confianca": float entre 0 e 1
}

Se IGNORAR, retorne:
{
  "tipo": "IGNORAR"
}

Retorne SOMENTE JSON válido, sem texto adicional.
```

### Prompt — Extração de imagem (recibo)

```
Você é um assistente financeiro. Analise a imagem do recibo e retorne SOMENTE JSON válido.

Data atual: {data_hoje}

Retorne:
{
  "tipo": "DESPESA",
  "descricao": "nome do estabelecimento",
  "valor": número float,
  "data": "YYYY-MM-DD",
  "confianca": float entre 0 e 1
}
```

---

## 7. Variáveis de Ambiente (.env)

```env
# Evolution API
EVOLUTION_API_URL=http://evolution:8080
EVOLUTION_API_KEY=...
EVOLUTION_INSTANCE=cookie-bot

# OpenAI API
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini

# Google Sheets
GOOGLE_SHEETS_ID=...
GOOGLE_CREDENTIALS_JSON=...   # JSON inline da service account

# WhatsApp
GRUPO_WHATSAPP_ID=...         # ID do grupo ou chat monitorado

# App
LOG_LEVEL=INFO
CONFIRMACAO_TTL_SEGUNDOS=300
CONFIANCA_MIN=0.85
```

---

## 8. Docker Compose

```yaml
services:
  app:
    build: ./app
    env_file: .env
    ports:
      - "8000:8000"
    restart: unless-stopped
    depends_on:
      - evolution

  evolution:
    image: atendai/evolution-api:v2
    ports:
      - "8080:8080"
    volumes:
      - evolution_data:/evolution/instances
    env_file: .env.evolution
    restart: unless-stopped

volumes:
  evolution_data:
```

---

## 9. Considerações de Segurança

| Superfície | Risco | Mitigação |
|---|---|---|
| Webhook público | Qualquer um pode postar no endpoint | Validar header `apikey` da Evolution API em todo request |
| Credenciais Google | Service account com acesso à planilha | Armazenar como variável de ambiente, nunca commitar |
| Chave Anthropic | Acesso ilimitado à API | Idem — `.env` fora do controle de versão |
| Mensagens do grupo | Outros membros do grupo podem acionar o bot | Filtrar por `sender` — aceitar apenas o número da dona |
| Injeção via mensagem | Usuário tenta manipular o prompt | Prompt isolado com instrução explícita de retornar só JSON |

---

## 10. Próximo Passo

Elaborar **Specs e Plano de Implementação** — breakdown em tarefas com ID, dependências e Definition of Done.
