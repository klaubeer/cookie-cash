import asyncio
import logging

from app.webhook.schema import PayloadWebhook

logger = logging.getLogger(__name__)

fila: asyncio.Queue[PayloadWebhook] = asyncio.Queue()


async def worker():
    logger.info("Worker da fila iniciado")
    while True:
        payload = await fila.get()
        chat_id = payload.data.key.remoteJid
        try:
            logger.info(f"Processando mensagem — chat_id={chat_id} tipo={payload.data.messageType}")
            from app.processador.dispatcher import despachar
            await despachar(payload)
            logger.info(f"Mensagem processada — chat_id={chat_id}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem — chat_id={chat_id} erro={e}")
        finally:
            fila.task_done()
