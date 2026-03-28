# CONTEXT.md

## STATUS GERAL DO PROJETO

- **Fase atual:** DESENVOLVIMENTO
- **Milestone atual:** Implementação concluída — pronto para deploy e testes end-to-end
- **Última decisão relevante:** TASK-10/11/12 implementadas — app 100% funcional, falta apenas configurar credenciais Google e fazer deploy
- **Próximo passo:** Configurar `.env` com `GOOGLE_SHEETS_ID` e `GOOGLE_CREDENTIALS_JSON`, depois subir com `docker compose up --build`

---

## FEATURES

| Status | Feature | Observações |
|--------|---------|-------------|
| ✅ DONE | Estrutura base + Docker | TASK-01 |
| ✅ DONE | Webhook Evolution API | TASK-02 |
| ✅ DONE | Fila assíncrona | TASK-03 |
| ✅ DONE | WhatsApp send/download | TASK-04 |
| ✅ DONE | Extrator LLM texto | TASK-05 |
| ✅ DONE | Transcrição áudio Whisper | TASK-06 |
| ✅ DONE | Extrator LLM imagem | TASK-07 |
| ✅ DONE | Dispatcher | TASK-08 |
| ✅ DONE | Gerenciador de confirmações | TASK-09 |
| ✅ DONE | Google Sheets | TASK-10 — adicionar_lancamento + obter_resumo_mes |
| ✅ DONE | Comando /resumo | TASK-11 — retorna receitas/despesas/saldo do mês atual |
| ✅ DONE | Hardening e deploy | TASK-12 — non-root user, .dockerignore, healthchecks |

---

## DECISÕES ATIVAS — NÃO ALTERAR SEM DISCUSSÃO

- **LLM:** GPT-4o mini (OpenAI) para visão + NLP — decidido em 27/03/2026
- **Áudio:** Whisper API (OpenAI) separado do LLM principal — decidido em 27/03/2026
- **Storage:** Google Sheets como único storage + dashboard, sem banco relacional — decidido em 27/03/2026
- **Estado de confirmação:** dict em memória com TTL de 5 min, sem Redis — decidido em 27/03/2026
- **Confiança mínima para salvar direto:** 0.85 — decidido em 27/03/2026
- **Mensagens ignoradas:** tipo IGNORAR retornado pelo LLM, sem resposta no chat — decidido em 27/03/2026
- **Workers uvicorn:** 1 worker (obrigatório — asyncio.Queue não é thread-safe entre workers) — decidido em 28/03/2026
