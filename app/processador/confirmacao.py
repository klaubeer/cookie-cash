import logging
import time
from dataclasses import dataclass, field

from app.config import config
from app.processador.schema import Transacao

logger = logging.getLogger(__name__)

_RESPOSTAS_SIM = {"sim", "s", "yes", "y", "isso", "correto", "certo", "pode", "ok"}
_RESPOSTAS_NAO = {"nao", "não", "n", "no", "errado", "cancela", "cancelar", "ignora"}


@dataclass
class EntradaPendente:
    transacao: Transacao
    criado_em: float = field(default_factory=time.monotonic)

    def expirado(self) -> bool:
        return (time.monotonic() - self.criado_em) > config.confirmacao_ttl_segundos


# chat_id -> EntradaPendente
_pendentes: dict[str, EntradaPendente] = {}


def registrar_pendente(chat_id: str, transacao: Transacao) -> None:
    _pendentes[chat_id] = EntradaPendente(transacao=transacao)
    logger.info(f"Confirmacao pendente registrada — chat_id={chat_id}")


def resolver(chat_id: str, resposta: str) -> Transacao | None:
    """
    Tenta resolver uma confirmacao pendente.
    Retorna a Transacao se confirmada, None se negada, cancelada ou sem pendencia.
    """
    entrada = _pendentes.get(chat_id)
    if not entrada:
        return None

    if entrada.expirado():
        del _pendentes[chat_id]
        logger.info(f"Confirmacao expirada descartada — chat_id={chat_id}")
        return None

    texto = resposta.strip().lower()

    if texto in _RESPOSTAS_SIM:
        transacao = entrada.transacao
        del _pendentes[chat_id]
        logger.info(f"Confirmacao aceita — chat_id={chat_id}")
        return transacao

    if texto in _RESPOSTAS_NAO:
        del _pendentes[chat_id]
        logger.info(f"Confirmacao recusada — chat_id={chat_id}")
        return None

    return None


def tem_pendente(chat_id: str) -> bool:
    entrada = _pendentes.get(chat_id)
    if not entrada:
        return False
    if entrada.expirado():
        del _pendentes[chat_id]
        return False
    return True


def formatar_pergunta(transacao: Transacao) -> str:
    tipo = "Venda" if transacao.tipo.value == "RECEITA" else "Compra"
    if transacao.cliente and transacao.itens:
        itens_str = "\n".join(f"  • {i.quantidade} {i.descricao}" for i in transacao.itens)
        return (
            f"Entendi: {tipo} de R${transacao.valor:.2f} para {transacao.cliente}\n"
            f"{itens_str}\n"
            f"em {transacao.data.strftime('%d/%m/%Y')}. Correto? (sim/nao)"
        )
    return (
        f"Entendi: {tipo} de R${transacao.valor:.2f} — {transacao.descricao} "
        f"em {transacao.data.strftime('%d/%m/%Y')}. Correto? (sim/nao)"
    )
