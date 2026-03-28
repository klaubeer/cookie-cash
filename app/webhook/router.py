import logging

from fastapi import APIRouter

from app.utils.fila import fila
from app.webhook.schema import PayloadWebhook

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook")
async def receber_webhook(payload: PayloadWebhook):
    logger.info(f"Webhook recebido — event={payload.event} chat_id={payload.data.key.remoteJid}")

    # Ignora eventos que não são mensagens recebidas
    if payload.event != "messages.upsert":
        return {"status": "ignorado"}

    # Ignora mensagens enviadas pelo próprio bot
    if payload.data.key.fromMe:
        return {"status": "ignorado"}

    logger.info(f"Mensagem recebida — chat_id={payload.data.key.remoteJid} tipo={payload.data.messageType}")

    await fila.put(payload)
    return {"status": "recebido"}
