import json
import logging
from base64 import b64encode
from datetime import date

from openai import AsyncOpenAI

from app.config import config
from app.processador.schema import ItemVenda, TipoTransacao, Transacao

logger = logging.getLogger(__name__)

_cliente = AsyncOpenAI(api_key=config.openai_api_key)

_PROMPT_TEXTO = """Você é um assistente financeiro de um negócio de cookies artesanais.
Analise a mensagem abaixo e classifique em uma das categorias:
- RECEITA: dinheiro recebido por uma venda já realizada
- DESPESA: dinheiro gasto em uma compra já realizada
- IGNORAR: qualquer outra coisa (lembrete, intenção futura, conversa, link, figurinha, etc.)

Mensagem: "{mensagem}"
Data atual: {data_hoje}

Se RECEITA ou DESPESA, retorne SOMENTE este JSON:
{{"tipo": "RECEITA" ou "DESPESA", "descricao": "descrição curta", "valor": número, "data": "YYYY-MM-DD", "confianca": número entre 0 e 1, "cliente": "nome do cliente ou null", "itens": [{{"descricao": "sabor/tipo do cookie", "quantidade": número}}]}}

O campo "cliente" deve ser preenchido somente quando a mensagem contiver o nome de um cliente (ex: "Debi", "Madalena"). Caso contrário, use null.
O campo "itens" deve listar os cookies pedidos com quantidade e descrição. Se não houver itens identificáveis, use [].

Exemplos de mensagem com cliente e itens:
"Debi\n1 de laranja\n1 limão\n24,00" → cliente="Debi", itens=[{{"descricao":"laranja","quantidade":1}},{{"descricao":"limão","quantidade":1}}]

Se IGNORAR, retorne SOMENTE:
{{"tipo": "IGNORAR"}}

Retorne SOMENTE JSON válido, sem texto adicional."""

_PROMPT_IMAGEM = """Você é um assistente financeiro de um negócio de cookies artesanais.
Analise a imagem do recibo abaixo.
Data atual: {data_hoje}

Retorne SOMENTE este JSON:
{{"tipo": "DESPESA", "descricao": "nome do estabelecimento", "valor": número, "data": "YYYY-MM-DD", "confianca": número entre 0 e 1}}

Se a imagem não for um recibo, retorne SOMENTE:
{{"tipo": "IGNORAR"}}

Retorne SOMENTE JSON válido, sem texto adicional."""


def _limpar_raw(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        raw = raw.rsplit("```", 1)[0]
    return raw.strip()


def _parse_resposta(raw: str) -> Transacao | None:
    try:
        dados = json.loads(_limpar_raw(raw))
    except json.JSONDecodeError:
        logger.error(f"Resposta do LLM não é JSON válido: {raw!r}")
        return None

    tipo_str = dados.get("tipo")
    if tipo_str == TipoTransacao.IGNORAR:
        return Transacao(
            tipo=TipoTransacao.IGNORAR,
            descricao="",
            valor=0.0,
            data=date.today(),
            confianca=1.0,
        )

    try:
        itens_raw = dados.get("itens") or []
        itens = [ItemVenda(descricao=i["descricao"], quantidade=int(i["quantidade"])) for i in itens_raw if i.get("descricao")]
        return Transacao(
            tipo=TipoTransacao(tipo_str),
            descricao=dados["descricao"],
            valor=float(dados["valor"]),
            data=date.fromisoformat(dados["data"]),
            confianca=float(dados["confianca"]),
            cliente=dados.get("cliente") or None,
            itens=itens,
        )
    except (KeyError, ValueError) as e:
        logger.error(f"Campos inválidos na resposta do LLM: {dados} — {e}")
        return None


async def extrair_de_texto(mensagem: str) -> Transacao | None:
    prompt = _PROMPT_TEXTO.format(mensagem=mensagem, data_hoje=date.today().isoformat())
    try:
        resp = await _cliente.chat.completions.create(
            model=config.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        raw = resp.choices[0].message.content or ""
        logger.info(f"LLM texto respondeu: {raw!r}")
        return _parse_resposta(raw)
    except Exception as e:
        logger.error(f"Erro na chamada LLM (texto): {e}")
        return None


async def extrair_de_imagem(dados_imagem: bytes, mime: str = "image/jpeg") -> Transacao | None:
    b64 = b64encode(dados_imagem).decode()
    prompt = _PROMPT_IMAGEM.format(data_hoje=date.today().isoformat())
    try:
        resp = await _cliente.chat.completions.create(
            model=config.openai_model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            }],
            temperature=0,
        )
        raw = resp.choices[0].message.content or ""
        logger.info(f"LLM imagem respondeu: {raw!r}")
        return _parse_resposta(raw)
    except Exception as e:
        logger.error(f"Erro na chamada LLM (imagem): {e}")
        return None
