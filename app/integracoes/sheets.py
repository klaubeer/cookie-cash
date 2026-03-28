import asyncio
import json
import logging
from datetime import date, datetime

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from app.config import config
from app.processador.schema import Transacao

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_ABA = "Lançamentos"
_MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _servico():
    info = json.loads(config.google_credentials_json)
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def _adicionar_lancamento_sync(transacao: Transacao) -> None:
    servico = _servico()
    linha = [
        transacao.data.strftime("%d/%m/%Y"),
        transacao.tipo.value,
        transacao.descricao,
        transacao.valor,
        transacao.origem,
        datetime.now().isoformat(timespec="seconds"),
    ]
    servico.spreadsheets().values().append(
        spreadsheetId=config.google_sheets_id,
        range=f"{_ABA}!A:F",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [linha]},
    ).execute()
    logger.info(f"Lançamento salvo — {transacao.tipo.value} R${transacao.valor:.2f}")


def _obter_resumo_mes_sync() -> dict:
    hoje = date.today()
    servico = _servico()
    result = servico.spreadsheets().values().get(
        spreadsheetId=config.google_sheets_id,
        range=f"{_ABA}!A2:D",
    ).execute()
    linhas = result.get("values", [])
    receitas = 0.0
    despesas = 0.0
    for linha in linhas:
        if len(linha) < 4:
            continue
        try:
            partes = linha[0].split("/")
            data_linha = date(int(partes[2]), int(partes[1]), int(partes[0]))
            if data_linha.month != hoje.month or data_linha.year != hoje.year:
                continue
            valor = float(str(linha[3]).replace(",", ".").replace("R$", "").strip())
            if linha[1] == "RECEITA":
                receitas += valor
            elif linha[1] == "DESPESA":
                despesas += valor
        except (ValueError, IndexError):
            continue
    return {
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
        "mes": _MESES[hoje.month - 1],
        "ano": hoje.year,
    }


async def adicionar_lancamento(transacao: Transacao) -> None:
    await asyncio.to_thread(_adicionar_lancamento_sync, transacao)


async def obter_resumo_mes() -> dict:
    return await asyncio.to_thread(_obter_resumo_mes_sync)
