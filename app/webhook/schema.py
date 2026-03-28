from typing import Any
from pydantic import BaseModel


class ChaveMensagem(BaseModel):
    remoteJid: str
    fromMe: bool
    id: str


class DadosMensagem(BaseModel):
    key: ChaveMensagem
    pushName: str | None = None
    message: dict[str, Any] | None = None
    messageType: str | None = None
    messageTimestamp: int | None = None


class PayloadWebhook(BaseModel):
    event: str
    instance: str
    data: DadosMensagem
    apikey: str | None = None
