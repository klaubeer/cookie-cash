# PRD — Cookie Finance Bot

> Versão 1.1 — 27/03/2026

---

## Visão Geral

Sistema de controle financeiro para negócio de cookies artesanais, operado inteiramente via WhatsApp. A usuária envia fotos de recibos, mensagens de texto ou áudios com vendas e despesas; uma IA processa as entradas e consolida tudo em uma planilha Google Sheets com saldo em tempo real.

---

## Problema

Empreendedora com pouco tempo gerencia um negócio de cookies sem controle financeiro estruturado. Não sabe com precisão quanto gasta em insumos nem quanto arrecada por vendas, tornando impossível uma análise real de lucratividade.

---

## Objetivo

Eliminar a fricção do controle financeiro tornando o WhatsApp — ferramenta já usada diariamente — o único ponto de entrada de dados. Zero apps novos, zero formulários, zero login.

---

## Usuários

| Perfil | Descrição |
|--------|-----------|
| Primário | Dona do negócio — usa WhatsApp o dia todo, sem tempo para apps separados |
| Secundário | Marido — acompanha o dashboard na planilha Google Sheets |

---

## Requisitos Funcionais

### RF-01 — Conexão WhatsApp
- Sistema conecta a um número WhatsApp via Evolution API (self-hosted)
- Monitora um grupo ou conversa designada
- Aceita três tipos de entrada: **imagem** (recibo de mercado), **texto** (registro de venda) e **áudio** (voz)

### RF-02 — Processamento de Despesas (foto de recibo)
- Extrai da imagem: data da compra, valor total, nome do estabelecimento
- Confirma no WhatsApp o que foi interpretado antes de salvar
- _(Fase futura: extração itemizada — produto, quantidade, preço unitário)_

### RF-03 — Processamento de Receitas e Despesas (texto ou áudio)
- Entende linguagem natural sem formato fixo:
  - "Joana, 3 cookies, R$45"
  - "vendi 5 pra Ana, 80 reais"
  - "comprei farinha, gastei 45 reais"
- Áudio é transcrito e processado da mesma forma que texto
- Extrai: tipo (venda ou compra), cliente/estabelecimento, quantidade, valor total, data (assume hoje se não informada)
- Confirma no WhatsApp o que foi registrado

### RF-04 — Persistência no Google Sheets
- Uma linha por transação (despesa ou receita)
- Campos por linha: data, tipo (DESPESA / RECEITA), descrição, valor, origem (foto / texto / áudio)
- Planilha atualizada em tempo real após cada mensagem processada

### RF-05 — Dashboard na Planilha
- **Aba "Lançamentos":** histórico completo linha a linha, filtrável por mês
- **Aba "Resumo":** total de receitas, total de despesas e saldo do período (mês atual por padrão)

### RF-06 — Feedback no WhatsApp
- Após processar qualquer entrada, o bot responde confirmando o registro
- Em caso de ambiguidade, pede confirmação antes de salvar
- Comando `/resumo` retorna o saldo do mês atual diretamente no WhatsApp

### RF-07 — Ignorar mensagens não financeiras
- Mensagens que não representam receita nem despesa são silenciosamente ignoradas — sem resposta no chat
- Exemplos de mensagens ignoradas:
  - Lembretes / intenções de compra futura: "comprar 5kg de farinha", "preciso de ovos"
  - Links externos, figurinhas, GIFs
  - Conversas gerais não financeiras: "oi", "tudo bem?", elogios, reclamações
- O LLM classifica a mensagem antes de qualquer processamento; se o resultado for `IGNORAR`, o fluxo encerra sem salvar nem responder

---

## Requisitos Não-Funcionais

| ID | Requisito |
|----|-----------|
| RNF-01 | Disponível 24/7 na VPS Hostinger via Docker Compose |
| RNF-02 | Zero configuração ou ação técnica por parte da usuária |
| RNF-03 | Custo operacional baixo — infraestrutura já existente, LLM estimado < R$20/mês |
| RNF-04 | Logs estruturados para facilitar debug |
| RNF-05 | Tolerância a falha: mensagem não é perdida se a planilha demorar a responder |

---

## Casos de Uso Principais

### CU-01 — Registro de despesa (recibo fotografado)
**Dado** que ela foi ao mercado e tem o recibo
**Quando** fotografa e envia no grupo do WhatsApp
**Então** o bot responde: *"Despesa registrada: R$87,50 no Mercadão em 27/03/2026"*
e a planilha ganha uma nova linha na aba Lançamentos

### CU-02 — Registro de venda (texto livre)
**Dado** que ela vendeu cookies para uma cliente
**Quando** envia "Joana levou 4 cookies, R$60"
**Então** o bot responde: *"Venda registrada: R$60,00 para Joana (4 cookies) em 27/03/2026"*
e a planilha ganha uma nova linha

### CU-03 — Consulta de saldo
**Dado** que ela quer saber como está o mês
**Quando** envia `/resumo`
**Então** o bot responde:
```
Março/2026
Receitas:  R$ 1.200,00
Despesas:  R$   340,00
─────────────────────
Saldo:     R$   860,00
```

### CU-04 — Entrada ambígua
**Dado** que a mensagem não ficou clara
**Quando** o bot identifica ambiguidade
**Então** responde: *"Entendi: venda de R$60 para Joana. Correto? (sim/não)"*
e aguarda confirmação antes de salvar

---

## Fora do Escopo — v1

- Controle de estoque de ingredientes
- Estatísticas por tipo de produto / custo por receita
- Múltiplos usuários ou negócios
- App mobile ou web próprio
- Integração com meios de pagamento (Pix, etc.)
- Nota fiscal

---

## Stack Técnica Proposta

| Componente | Tecnologia | Justificativa |
|---|---|---|
| WhatsApp | Evolution API v2 (self-hosted, Docker) | Gratuito, ativo, amplamente usado no Brasil |
| Backend | Python + FastAPI | Simples, bom ecossistema para IA |
| LLM / Visão | OpenAI API (gpt-4o-mini) | OCR + NLP, custo ~6,5× menor que Claude Haiku ($0,15/$0,60 por M tokens) |
| Transcrição de áudio | OpenAI Whisper API | Modelo separado, custo baixo por minuto de áudio |
| Planilha | Google Sheets API v4 | Já familiar, zero custo, acesso fácil pelo celular |
| Infraestrutura | Docker Compose na VPS Hostinger | Infra já existente, sem custo adicional |

---

## Critérios de Aceite do MVP

- [ ] Bot conecta ao WhatsApp via Evolution API e responde mensagens no grupo
- [ ] Foto de recibo → linha de despesa na planilha com data, valor e estabelecimento
- [ ] Texto de venda em linguagem natural → linha de receita na planilha
- [ ] Áudio transcrito e processado da mesma forma que texto
- [ ] Planilha contém aba "Lançamentos" e aba "Resumo" com saldo do mês
- [ ] Comando `/resumo` retorna saldo atual no WhatsApp
- [ ] Bot confirma cada lançamento com mensagem de texto
- [ ] Sistema sobe com `docker compose up` na VPS

---

## Próximo Passo

Elaborar o **SDD** (Software Design Document) com arquitetura detalhada, fluxo de mensagens e estrutura do banco/planilha.
