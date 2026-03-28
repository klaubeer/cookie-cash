# CONTEXT.md

## STATUS GERAL DO PROJETO

- **Fase atual:** PRODUÇÃO
- **Milestone atual:** App em produção na VPS, todos os fluxos testados e funcionando
- **Última decisão relevante:** Aba Resumo com dropdown de período (03/2026 em diante) + Total Geral sem filtro
- **Próximo passo:** Monitorar uso em produção

---

## FEATURES

| Status | Feature | Observações |
|--------|---------|-------------|
| ✅ DONE | Estrutura base + Docker | TASK-01 |
| ✅ DONE | Webhook Evolution API | TASK-02 — validação apikey removida (Evo v2 não envia) |
| ✅ DONE | Fila assíncrona | TASK-03 |
| ✅ DONE | WhatsApp send/download | TASK-04 — fix: passar key no getBase64FromMediaMessage |
| ✅ DONE | Extrator LLM texto | TASK-05 — fix: strip markdown code block da resposta |
| ✅ DONE | Transcrição áudio Whisper | TASK-06 |
| ✅ DONE | Extrator LLM imagem | TASK-07 |
| ✅ DONE | Dispatcher | TASK-08 |
| ✅ DONE | Gerenciador de confirmações | TASK-09 |
| ✅ DONE | Google Sheets | TASK-10 — adicionar_lancamento + obter_resumo_mes |
| ✅ DONE | Comando /resumo | TASK-11 |
| ✅ DONE | Hardening e deploy | TASK-12 — non-root user, .dockerignore, healthchecks |
| ✅ DONE | Aba Resumo | Dropdown 03/2026 em diante + Total Geral |

---


## DECISÕES ATIVAS — NÃO ALTERAR SEM DISCUSSÃO

- **LLM:** GPT-4o mini (OpenAI) para visão + NLP — decidido em 27/03/2026
- **Áudio:** Whisper API (OpenAI) separado do LLM principal — decidido em 27/03/2026
- **Storage:** Google Sheets como único storage + dashboard, sem banco relacional — decidido em 27/03/2026
- **Estado de confirmação:** dict em memória com TTL de 5 min, sem Redis — decidido em 27/03/2026
- **Confiança mínima para salvar direto:** 0.85 — decidido em 27/03/2026
- **Mensagens ignoradas:** tipo IGNORAR retornado pelo LLM, sem resposta no chat — decidido em 27/03/2026
- **Workers uvicorn:** 1 worker (obrigatório — asyncio.Queue não é thread-safe entre workers) — decidido em 28/03/2026
- **Webhook sem validação apikey:** Evolution API v2 não envia apikey no webhook — decidido em 28/03/2026
