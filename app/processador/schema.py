from datetime import date
from enum import Enum

from pydantic import BaseModel


class TipoTransacao(str, Enum):
    RECEITA = "RECEITA"
    DESPESA = "DESPESA"
    IGNORAR = "IGNORAR"


class Transacao(BaseModel):
    tipo: TipoTransacao
    descricao: str
    valor: float
    data: date
    confianca: float
    origem: str = "texto"
