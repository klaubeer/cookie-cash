# Specs e Plano de Implementação — Cookie Finance Bot

> Versão 1.0 — 27/03/2026

---

## Ordem de Implementação

```
TASK-01 → TASK-02 → TASK-03
                         ↓
              TASK-04 → TASK-05 → TASK-06
                                      ↓
                         TASK-07 → TASK-08
                                      ↓
                    TASK-09 → TASK-10 → TASK-11
                                             ↓
                                         TASK-12
```

---

## Tarefas

### TASK-01 — Estrutura base do projeto

**Descrição:** Criar estrutura de pastas, `pyproject.toml` (ou `requirements.txt`), `Dockerfile`, `.env.example` e `config.py` com todas as variáveis de ambiente via pydantic-settings.

**Depende de:** —

**Definition of Done:**
- `docker compose up` sobe o container sem erros
- `GET /health` retorna `{"status": "ok"}`
- Todas as variáveis do `.env.example` são lidas e validadas na inicialização; app falha com mensagem clara se alguma estiver faltando

---

### TASK-02 — Integração Evolution API — receber mensagens

**Descrição:** Implementar `webhook/router.py` com `POST /webhook`. Validar header `apikey`. Deserializar payload da Evolution API via `webhook/schema.py`. Responder 200 imediatamente.

**Depende de:** TASK-01

**Definition of Done:**
- Evento simulado via `curl` é recebido, logado e retorna 200 em < 200 ms
- Request com `apikey` inválida retorna 401
- Payload malformado retorna 422 sem derrubar o app

---

### TASK-03 — Fila assíncrona de processamento

**Descrição:** Implementar `utils/fila.py` com `asyncio.Queue`. Worker consome mensagens em background. Webhook enfileira e retorna 200 sem esperar o processamento.

**Depende de:** TASK-02

**Definition of Done:**
- Duas mensagens enviadas simultaneamente são processadas sequencialmente (sem race condition)
- Worker loga início e fim de cada processamento
- Falha no processamento de uma mensagem não para a fila

---

### TASK-04 — Integração WhatsApp — enviar mensagens

**Descrição:** Implementar `integrações/whatsapp.py` com função `enviar_texto(chat_id, texto)` e `baixar_midia(url)` via Evolution API.

**Depende de:** TASK-01

**Definition of Done:**
- Função envia mensagem de texto para número real no WhatsApp
- `baixar_midia` retorna bytes do arquivo (imagem ou áudio)
- Erros de rede são logados sem derrubar o app

---

### TASK-05 — Extrator LLM — texto e áudio

**Descrição:** Implementar `processador/extrator.py` para texto. Chamar GPT-4o mini com o prompt definido no SDD. Parsear resposta JSON e retornar `Transacao` ou `tipo == IGNORAR`.

**Depende de:** TASK-03, TASK-04

**Definition of Done:**
- "Joana, 3 cookies, R$45" → `Transacao(tipo=RECEITA, valor=45.0, descricao="Joana — 3 cookies")`
- "comprar farinha" → `tipo == IGNORAR` (sem resposta no chat)
- Resposta inválida do LLM é logada e tratada sem crash
- Campo `confianca` é retornado corretamente

---

### TASK-06 — Transcrição de áudio (Whisper)

**Descrição:** Implementar `integrações/audio.py`. Baixar o arquivo de áudio via `whatsapp.baixar_midia`, enviar para OpenAI Whisper API, retornar texto transcrito.

**Depende de:** TASK-04

**Definition of Done:**
- Áudio de voz enviado no WhatsApp é transcrito para texto
- Texto transcrito é passado para o extrator (TASK-05) sem tratamento especial
- Erros de transcrição logados; bot responde "Não consegui entender o áudio, pode digitar?"

---

### TASK-07 — Extrator LLM — imagem (recibo)

**Descrição:** Estender `extrator.py` para suportar entrada de imagem. Usar GPT-4o mini vision com o prompt de recibo definido no SDD.

**Depende de:** TASK-05

**Definition of Done:**
- Foto de recibo real → `Transacao(tipo=DESPESA, valor=X, descricao="nome do mercado", data="YYYY-MM-DD")`
- Imagem que não é recibo → `tipo == IGNORAR`
- Imagem ilegível → `confianca < 0.85` → fluxo de confirmação acionado

---

### TASK-08 — Dispatcher — roteador de tipos de mensagem

**Descrição:** Implementar `processador/dispatcher.py`. Identificar tipo da mensagem (texto / áudio / imagem / outro) e delegar ao handler correto. Mensagens do tipo "outro" (sticker, vídeo, link) são ignoradas silenciosamente.

**Depende de:** TASK-06, TASK-07

**Definition of Done:**
- Texto → extrator de texto
- Áudio → audio.py → extrator de texto
- Imagem → extrator de imagem
- Sticker / vídeo / link → ignorado, sem resposta
- Apenas mensagens do `GRUPO_WHATSAPP_ID` configurado são processadas; demais são ignoradas

---

### TASK-09 — Gerenciador de confirmações

**Descrição:** Implementar `processador/confirmacao.py`. Se `confianca < CONFIANCA_MIN`, salvar `PendingEntry` no dict com TTL. Aguardar resposta "sim"/"não". TTL expirado → descartar silenciosamente.

**Depende de:** TASK-08

**Definition of Done:**
- Mensagem de baixa confiança gera pergunta de confirmação no WhatsApp
- Resposta "sim" → salva no Sheets → confirma no chat
- Resposta "não" → descarta → "Ok, ignorei esse lançamento."
- TTL de 5 min expirado → entrada descartada sem resposta
- Alta confiança → salva direto, sem perguntar

---

### TASK-10 — Integração Google Sheets

**Descrição:** Implementar `integrações/sheets.py` com `adicionar_lancamento(transacao)` e `obter_resumo_mes()`. Criar a planilha com as abas "Lançamentos" e "Resumo" (com fórmulas SUMIFS).

**Depende de:** TASK-09

**Definition of Done:**
- `adicionar_lancamento` appenda uma linha na aba Lançamentos com os 6 campos definidos no SDD
- `obter_resumo_mes` lê os totais calculados pelas fórmulas da aba Resumo
- Erro de API do Sheets é logado; mensagem não é perdida (retentativa 1×)

---

### TASK-11 — Comando /resumo

**Descrição:** No dispatcher, detectar mensagem `/resumo`. Chamar `sheets.obter_resumo_mes()` e formatar resposta no padrão definido no CU-03 do PRD.

**Depende de:** TASK-10

**Definition of Done:**
- Enviar `/resumo` no WhatsApp retorna saldo formatado do mês atual
- Formato exato:
  ```
  Março/2026
  Receitas:  R$ 1.200,00
  Despesas:  R$   340,00
  ─────────────────────
  Saldo:     R$   860,00
  ```

---

### TASK-12 — Hardening e deploy

**Descrição:** Revisar logs estruturados (JSON), variáveis de ambiente no `.env.example`, `docker-compose.yml` final com restart policy, e validar checklist de segurança do SDD.

**Depende de:** TASK-11

**Definition of Done:**
- `docker compose up` na VPS sobe tudo sem intervenção manual
- Todos os critérios de aceite do MVP no PRD estão marcados
- Nenhuma credencial hardcoded no código ou no repositório
- Logs em JSON com `timestamp`, `level`, `mensagem`, `chat_id`

---

## Resumo

| ID | Descrição | Depende de | Status |
|----|-----------|------------|--------|
| TASK-01 | Estrutura base + Docker | — | 📋 PLANNED |
| TASK-02 | Webhook Evolution API | TASK-01 | 📋 PLANNED |
| TASK-03 | Fila assíncrona | TASK-02 | 📋 PLANNED |
| TASK-04 | WhatsApp — enviar / baixar mídia | TASK-01 | 📋 PLANNED |
| TASK-05 | Extrator LLM — texto | TASK-03, TASK-04 | 📋 PLANNED |
| TASK-06 | Transcrição de áudio (Whisper) | TASK-04 | 📋 PLANNED |
| TASK-07 | Extrator LLM — imagem | TASK-05 | 📋 PLANNED |
| TASK-08 | Dispatcher | TASK-06, TASK-07 | 📋 PLANNED |
| TASK-09 | Gerenciador de confirmações | TASK-08 | 📋 PLANNED |
| TASK-10 | Google Sheets | TASK-09 | 📋 PLANNED |
| TASK-11 | Comando /resumo | TASK-10 | 📋 PLANNED |
| TASK-12 | Hardening e deploy | TASK-11 | 📋 PLANNED |
