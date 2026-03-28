import base64
import logging
from typing import Any

import httpx

from app.config import config

logger = logging.getLogger(__name__)

_BASE = f"{config.evolution_api_url}/message"
_HEADERS = {"apikey": config.evolution_api_key}


async def enviar_texto(chat_id: str, texto: str) -> None:
    url = f"{_BASE}/sendText/{config.evolution_instance}"
    payload = {"number": chat_id, "text": texto}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json=payload, headers=_HEADERS)
            resp.raise_for_status()
            logger.info(f"Mensagem enviada — chat_id={chat_id}")
        except httpx.HTTPError as e:
            logger.error(f"Erro ao enviar mensagem — chat_id={chat_id} erro={e}")
            raise


async def baixar_midia(url: str) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.get(url, headers=_HEADERS)
            resp.raise_for_status()
            return resp.content
        except httpx.HTTPError as e:
            logger.error(f"Erro ao baixar mídia — url={url} erro={e}")
            raise


async def baixar_midia_mensagem(message: dict[str, Any]) -> bytes:
    """Usa o endpoint da Evolution API para obter mídia de uma mensagem como base64."""
    url = f"{config.evolution_api_url}/chat/getBase64FromMediaMessage/{config.evolution_instance}"
    body = {"message": {"message": message}, "convertToMp4": False}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(url, json=body, headers=_HEADERS)
            resp.raise_for_status()
            dados = resp.json()
            return base64.b64decode(dados["base64"])
        except (httpx.HTTPError, KeyError, ValueError) as e:
            logger.error(f"Erro ao baixar mídia da mensagem: {e}")
            raise
