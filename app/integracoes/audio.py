import io
import logging

from openai import AsyncOpenAI

from app.config import config

logger = logging.getLogger(__name__)

_cliente = AsyncOpenAI(api_key=config.openai_api_key)


async def transcrever(dados: bytes, mime: str = "audio/ogg") -> str | None:
    """
    Recebe bytes de áudio e retorna o texto transcrito.
    Retorna None se a transcrição falhar.
    """
    extensao = _extensao(mime)
    arquivo = io.BytesIO(dados)
    arquivo.name = f"audio.{extensao}"

    try:
        resp = await _cliente.audio.transcriptions.create(
            model="whisper-1",
            file=arquivo,
            language="pt",
        )
        texto = resp.text.strip()
        logger.info(f"Áudio transcrito: {texto!r}")
        return texto
    except Exception as e:
        logger.error(f"Erro na transcrição de áudio: {e}")
        return None


def _extensao(mime: str) -> str:
    mapa = {
        "audio/ogg":  "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4":  "mp4",
        "audio/webm": "webm",
        "audio/wav":  "wav",
    }
    return mapa.get(mime, "ogg")
