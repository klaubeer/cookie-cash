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


def _configurar_resumo_sync() -> None:
    servico = _servico()
    sid = config.google_sheets_id

    # Cabeçalho Lançamentos — só escreve se ainda não existir
    existente = servico.spreadsheets().values().get(
        spreadsheetId=sid,
        range="Lançamentos!A1",
    ).execute()
    if not existente.get("values"):
        servico.spreadsheets().values().update(
            spreadsheetId=sid,
            range="Lançamentos!A1:F1",
            valueInputOption="USER_ENTERED",
            body={"values": [["Data", "Tipo", "Descrição", "Valor (R$)", "Origem", "Timestamp"]]},
        ).execute()

    # Aba Resumo — mês atual fixo, sem seletor de período
    # Separador ";" para locale pt-BR do Google Sheets
    mes_inicio = '=DATE(YEAR(TODAY());MONTH(TODAY());1)'
    mes_fim    = '=EOMONTH(TODAY();0)'
    receitas   = '=SUMPRODUCT((IFERROR(DATEVALUE(Lançamentos!$A$2:$A$500);0)>=$B$2)*(IFERROR(DATEVALUE(Lançamentos!$A$2:$A$500);0)<=$B$3)*(Lançamentos!$B$2:$B$500="RECEITA")*IFERROR(Lançamentos!$D$2:$D$500;0))'
    despesas   = '=SUMPRODUCT((IFERROR(DATEVALUE(Lançamentos!$A$2:$A$500);0)>=$B$2)*(IFERROR(DATEVALUE(Lançamentos!$A$2:$A$500);0)<=$B$3)*(Lançamentos!$B$2:$B$500="DESPESA")*IFERROR(Lançamentos!$D$2:$D$500;0))'
    valores_resumo = [
        ["Cookie Finance — Resumo", ""],   # A1
        ["De",   mes_inicio],              # A2:B2
        ["Até",  mes_fim],                 # A3:B3
        [],                                # A4
        ["RECEITAS", receitas],            # A5:B5
        ["DESPESAS", despesas],            # A6:B6
        [],                                # A7
        ["SALDO", "=B5-B6"],              # A8:B8
    ]
    servico.spreadsheets().values().update(
        spreadsheetId=sid,
        range="Resumo!A1:B8",
        valueInputOption="USER_ENTERED",
        body={"values": valores_resumo},
    ).execute()
    logger.info("Aba Resumo configurada com sucesso")


async def adicionar_lancamento(transacao: Transacao) -> None:
    await asyncio.to_thread(_adicionar_lancamento_sync, transacao)


async def obter_resumo_mes() -> dict:
    return await asyncio.to_thread(_obter_resumo_mes_sync)


async def configurar_resumo() -> None:
    await asyncio.to_thread(_configurar_resumo_sync)
