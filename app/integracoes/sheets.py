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
_ABA_PEDIDOS = "Pedidos"
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


def _meses_desde_inicio() -> list[str]:
    """Gera meses de 03/2026 até hoje + 2 meses à frente."""
    inicio = date(2026, 3, 1)
    hoje = date.today()
    fim = date(hoje.year + (1 if hoje.month > 10 else 0), (hoje.month + 2) % 12 or 12, 1)
    meses = []
    atual = inicio
    while atual <= fim:
        meses.append(f"{atual.month:02d}/{atual.year}")
        mes = atual.month + 1
        ano = atual.year + (1 if mes > 12 else 0)
        mes = mes if mes <= 12 else 1
        atual = date(ano, mes, 1)
    return meses


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

    # Gera lista de 03/2026 até hoje + 2 meses
    meses = _meses_desde_inicio()
    hoje = date.today()
    mes_atual = f"{hoje.month:02d}/{hoje.year}"

    # Fórmulas — B2 contém o mês selecionado no formato MM/YYYY
    # VALUE(LEFT(B2;2)) = mês, VALUE(RIGHT(B2;4)) = ano
    de  = '=DATE(VALUE(RIGHT(B2;4));VALUE(LEFT(B2;2));1)'
    ate = '=EOMONTH(DATE(VALUE(RIGHT(B2;4));VALUE(LEFT(B2;2));1);0)'
    receitas = '=SUMPRODUCT((IFERROR(DATEVALUE(Lançamentos!$A$2:$A$500);0)>=$B$3)*(IFERROR(DATEVALUE(Lançamentos!$A$2:$A$500);0)<=$B$4)*(Lançamentos!$B$2:$B$500="RECEITA")*IFERROR(Lançamentos!$D$2:$D$500;0))'
    despesas = '=SUMPRODUCT((IFERROR(DATEVALUE(Lançamentos!$A$2:$A$500);0)>=$B$3)*(IFERROR(DATEVALUE(Lançamentos!$A$2:$A$500);0)<=$B$4)*(Lançamentos!$B$2:$B$500="DESPESA")*IFERROR(Lançamentos!$D$2:$D$500;0))'

    # Limpa a aba antes de reescrever para não deixar lixo de writes anteriores
    servico.spreadsheets().values().clear(
        spreadsheetId=sid,
        range="Resumo!A1:Z50",
    ).execute()

    receitas_total = '=SUMIF(Lançamentos!$B$2:$B$500;"RECEITA";Lançamentos!$D$2:$D$500)'
    despesas_total = '=SUMIF(Lançamentos!$B$2:$B$500;"DESPESA";Lançamentos!$D$2:$D$500)'

    valores_resumo = [
        ["Cookie Finance — Resumo", ""],  # A1
        ["Período",  mes_atual],          # A2:B2  ← dropdown aqui
        ["De",       de],                 # A3:B3
        ["Até",      ate],                # A4:B4
        ["", ""],                         # A5
        ["RECEITAS", receitas],           # A6:B6
        ["DESPESAS", despesas],           # A7:B7
        ["", ""],                         # A8
        ["SALDO",    "=B6-B7"],          # A9:B9
        ["", ""],                         # A10
        ["TOTAL GERAL", ""],             # A11
        ["RECEITAS", receitas_total],    # A12:B12
        ["DESPESAS", despesas_total],    # A13:B13
        ["", ""],                         # A14
        ["SALDO",    "=B12-B13"],        # A15:B15
    ]
    servico.spreadsheets().values().update(
        spreadsheetId=sid,
        range="Resumo!A1:B15",
        valueInputOption="USER_ENTERED",
        body={"values": valores_resumo},
    ).execute()

    # Busca o sheetId da aba Resumo para aplicar data validation
    meta = servico.spreadsheets().get(spreadsheetId=sid).execute()
    sheet_id = next(
        s["properties"]["sheetId"]
        for s in meta["sheets"]
        if s["properties"]["title"] == "Resumo"
    )

    # Dropdown com os últimos 12 meses na célula B2
    opcoes = [{"userEnteredValue": m} for m in meses]
    servico.spreadsheets().batchUpdate(
        spreadsheetId=sid,
        body={"requests": [{
            "setDataValidation": {
                "range": {"sheetId": sheet_id, "startRowIndex": 1, "endRowIndex": 2, "startColumnIndex": 1, "endColumnIndex": 2},
                "rule": {
                    "condition": {"type": "ONE_OF_LIST", "values": opcoes},
                    "showCustomUi": True,
                    "strict": True,
                },
            }
        }]},
    ).execute()

    logger.info("Aba Resumo configurada com sucesso")


def _adicionar_pedido_sync(transacao: Transacao) -> None:
    if not transacao.cliente:
        return
    servico = _servico()
    itens_str = ", ".join(f"{i.quantidade} {i.descricao}" for i in transacao.itens)
    total_cookies = sum(i.quantidade for i in transacao.itens)
    linha = [
        transacao.data.strftime("%d/%m/%Y"),
        transacao.cliente,
        itens_str,
        total_cookies,
        transacao.valor,
        datetime.now().isoformat(timespec="seconds"),
    ]
    servico.spreadsheets().values().append(
        spreadsheetId=config.google_sheets_id,
        range=f"{_ABA_PEDIDOS}!A:F",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [linha]},
    ).execute()
    logger.info(f"Pedido salvo — cliente={transacao.cliente} cookies={total_cookies}")


def _obter_clientes_sync() -> list[dict]:
    servico = _servico()
    result = servico.spreadsheets().values().get(
        spreadsheetId=config.google_sheets_id,
        range=f"{_ABA_PEDIDOS}!A2:F",
    ).execute()
    linhas = result.get("values", [])
    totais: dict[str, dict] = {}
    for linha in linhas:
        if len(linha) < 5:
            continue
        try:
            cliente = linha[1].strip()
            total_cookies = int(float(str(linha[3]).replace(",", ".")))
            valor = float(str(linha[4]).replace(",", ".").replace("R$", "").strip())
        except (ValueError, IndexError):
            continue
        if cliente not in totais:
            totais[cliente] = {"cliente": cliente, "total_cookies": 0, "total_valor": 0.0}
        totais[cliente]["total_cookies"] += total_cookies
        totais[cliente]["total_valor"] += valor
    return sorted(totais.values(), key=lambda x: x["total_cookies"], reverse=True)


def _obter_sabores_sync() -> list[dict]:
    servico = _servico()
    result = servico.spreadsheets().values().get(
        spreadsheetId=config.google_sheets_id,
        range=f"{_ABA_PEDIDOS}!C2:C",
    ).execute()
    linhas = result.get("values", [])
    totais: dict[str, int] = {}
    for linha in linhas:
        if not linha:
            continue
        for parte in linha[0].split(","):
            parte = parte.strip()
            if not parte:
                continue
            try:
                espaco = parte.index(" ")
                qtd = int(parte[:espaco])
                sabor = parte[espaco + 1:].strip().lower()
            except (ValueError, IndexError):
                continue
            totais[sabor] = totais.get(sabor, 0) + qtd
    return sorted(
        [{"sabor": s, "quantidade": q} for s, q in totais.items()],
        key=lambda x: x["quantidade"],
        reverse=True,
    )


def _configurar_pedidos_sync() -> None:
    servico = _servico()
    sid = config.google_sheets_id

    meta = servico.spreadsheets().get(spreadsheetId=sid).execute()
    abas_existentes = {s["properties"]["title"] for s in meta["sheets"]}

    if _ABA_PEDIDOS not in abas_existentes:
        servico.spreadsheets().batchUpdate(
            spreadsheetId=sid,
            body={"requests": [{"addSheet": {"properties": {"title": _ABA_PEDIDOS}}}]},
        ).execute()
        logger.info(f"Aba '{_ABA_PEDIDOS}' criada")

    existente = servico.spreadsheets().values().get(
        spreadsheetId=sid,
        range=f"{_ABA_PEDIDOS}!A1",
    ).execute()
    if not existente.get("values"):
        servico.spreadsheets().values().update(
            spreadsheetId=sid,
            range=f"{_ABA_PEDIDOS}!A1:F1",
            valueInputOption="USER_ENTERED",
            body={"values": [["Data", "Cliente", "Itens", "Total Cookies", "Valor (R$)", "Timestamp"]]},
        ).execute()
        logger.info("Cabeçalho da aba Pedidos configurado")


async def adicionar_lancamento(transacao: Transacao) -> None:
    await asyncio.to_thread(_adicionar_lancamento_sync, transacao)


async def adicionar_pedido(transacao: Transacao) -> None:
    await asyncio.to_thread(_adicionar_pedido_sync, transacao)


async def obter_clientes() -> list[dict]:
    return await asyncio.to_thread(_obter_clientes_sync)


async def obter_sabores() -> list[dict]:
    return await asyncio.to_thread(_obter_sabores_sync)


async def obter_resumo_mes() -> dict:
    return await asyncio.to_thread(_obter_resumo_mes_sync)


async def configurar_resumo() -> None:
    await asyncio.to_thread(_configurar_resumo_sync)


async def configurar_pedidos() -> None:
    await asyncio.to_thread(_configurar_pedidos_sync)
