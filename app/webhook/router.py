import logging

from fastapi import APIRouter, Header, HTTPException

from app.config import config
from app.utils.fila import fila
from app.webhook.schema import PayloadWebhook

logger = logging.getLogger(__name__)

router = APIRouter()


def _validar_apikey(apikey_header: str | None, apikey_body: str | None) -> None:
    chave = apikey_header or apikey_body
    if chave != config.evolution_api_key:
        raise HTTPException(status_code=401, detail="apikey inválida")


@router.post("/webhook")
async def receber_webhook(
    payload: PayloadWebhook,
    apikey: str | None = Header(default=None),
):
    _validar_apikey(apikey, payload.apikey)

    # Ignora eventos que não são mensagens recebidas
    if payload.event != "messages.upsert":
        return {"status": "ignorado"}

    # Ignora mensagens enviadas pelo próprio bot
    if payload.data.key.fromMe:
        return {"status": "ignorado"}

    logger.info(f"Mensagem recebida — chat_id={payload.data.key.remoteJid} tipo={payload.data.messageType}")

    await fila.put(payload)
    return {"status": "recebido"}
