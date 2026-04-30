import logging

from app.config import config
from app.integracoes.audio import transcrever
from app.integracoes.sheets import adicionar_lancamento, adicionar_pedido, obter_clientes, obter_resumo_mes, obter_sabores
from app.integracoes.whatsapp import baixar_midia_mensagem, enviar_texto
from app.processador import confirmacao as confirmacao_mgr
from app.processador.extrator import extrair_de_imagem, extrair_de_texto
from app.processador.schema import TipoTransacao, Transacao
from app.webhook.schema import PayloadWebhook

logger = logging.getLogger(__name__)

_TIPOS_TEXTO  = {"conversation", "extendedTextMessage"}
_TIPOS_AUDIO  = {"audioMessage", "pttMessage"}
_TIPOS_IMAGEM = {"imageMessage"}
_COMANDO_RESUMO   = "/resumo"
_COMANDO_CLIENTES = "/clientes"
_COMANDO_SABORES  = "/sabores"


async def despachar(payload: PayloadWebhook) -> None:
    chat_id = payload.data.key.remoteJid
    message = payload.data.message or {}
    tipo    = payload.data.messageType or ""

    # Filtra: só processa o grupo/chat configurado
    if chat_id != config.grupo_whatsapp_id:
        logger.info(f"Mensagem de chat nao monitorado ignorada — chat_id={chat_id}")
        return

    # Resposta de confirmacao pendente tem prioridade
    if tipo in _TIPOS_TEXTO:
        texto = _extrair_texto_mensagem(message)
        if texto and confirmacao_mgr.tem_pendente(chat_id):
            await _resolver_confirmacao(chat_id, texto)
            return

        # Comandos
        if texto and texto.strip().lower() == _COMANDO_RESUMO:
            await _enviar_resumo(chat_id)
            return

        if texto and texto.strip().lower() == _COMANDO_CLIENTES:
            await _enviar_clientes(chat_id)
            return

        if texto and texto.strip().lower() == _COMANDO_SABORES:
            await _enviar_sabores(chat_id)
            return

    transacao: Transacao | None = None

    if tipo in _TIPOS_TEXTO:
        texto = _extrair_texto_mensagem(message)
        if not texto:
            return
        transacao = await extrair_de_texto(texto)
        if transacao:
            transacao.origem = "texto"

    elif tipo in _TIPOS_AUDIO:
        try:
            dados = await baixar_midia_mensagem(payload.data.key.model_dump(), message)
        except Exception:
            await enviar_texto(chat_id, "Nao consegui entender o audio, pode digitar?")
            return
        texto_transcrito = await transcrever(dados)
        if not texto_transcrito:
            await enviar_texto(chat_id, "Nao consegui entender o audio, pode digitar?")
            return
        transacao = await extrair_de_texto(texto_transcrito)
        if transacao:
            transacao.origem = "áudio"

    elif tipo in _TIPOS_IMAGEM:
        mime = message.get("imageMessage", {}).get("mimetype", "image/jpeg")
        try:
            dados = await baixar_midia_mensagem(payload.data.key.model_dump(), message)
        except Exception:
            await enviar_texto(chat_id, "Nao consegui ler a imagem, tente novamente.")
            return
        transacao = await extrair_de_imagem(dados, mime)
        if transacao:
            transacao.origem = "foto"

    else:
        logger.info(f"Tipo de mensagem ignorado — tipo={tipo} chat_id={chat_id}")
        return

    if transacao is None:
        logger.error(f"Extracao falhou — chat_id={chat_id} tipo={tipo}")
        await enviar_texto(chat_id, "Nao entendi essa mensagem. Pode repetir de outro jeito?")
        return

    if transacao.tipo == TipoTransacao.IGNORAR:
        logger.info(f"Mensagem classificada como IGNORAR — chat_id={chat_id}")
        return

    await _encaminhar_transacao(chat_id, transacao)


async def _encaminhar_transacao(chat_id: str, transacao: Transacao) -> None:
    if transacao.confianca >= config.confianca_min:
        await adicionar_lancamento(transacao)
        if transacao.cliente:
            await adicionar_pedido(transacao)
        tipo_str = "Venda" if transacao.tipo.value == "RECEITA" else "Compra"
        await enviar_texto(
            chat_id,
            f"{tipo_str} registrada: R${transacao.valor:.2f} — {transacao.descricao} "
            f"em {transacao.data.strftime('%d/%m/%Y')}."
        )
    else:
        confirmacao_mgr.registrar_pendente(chat_id, transacao)
        await enviar_texto(chat_id, confirmacao_mgr.formatar_pergunta(transacao))


async def _resolver_confirmacao(chat_id: str, resposta: str) -> None:
    transacao = confirmacao_mgr.resolver(chat_id, resposta)
    if transacao:
        await adicionar_lancamento(transacao)
        if transacao.cliente:
            await adicionar_pedido(transacao)
        tipo_str = "Venda" if transacao.tipo.value == "RECEITA" else "Compra"
        await enviar_texto(
            chat_id,
            f"{tipo_str} registrada: R${transacao.valor:.2f} — {transacao.descricao} "
            f"em {transacao.data.strftime('%d/%m/%Y')}."
        )
    else:
        await enviar_texto(chat_id, "Ok, ignorei esse lancamento.")


async def _enviar_clientes(chat_id: str) -> None:
    try:
        clientes = await obter_clientes()
    except Exception as e:
        logger.error(f"Erro ao buscar clientes — chat_id={chat_id} erro={e}")
        await enviar_texto(chat_id, "Nao consegui buscar os clientes agora. Tente de novo em instantes.")
        return
    if not clientes:
        await enviar_texto(chat_id, "Nenhum pedido registrado ainda.")
        return
    linhas = ["Clientes (acumulado):"]
    for c in clientes:
        linhas.append(f"• {c['cliente']}: {c['total_cookies']} cookies — R${c['total_valor']:.2f}")
    await enviar_texto(chat_id, "\n".join(linhas))


async def _enviar_sabores(chat_id: str) -> None:
    try:
        sabores = await obter_sabores()
    except Exception as e:
        logger.error(f"Erro ao buscar sabores — chat_id={chat_id} erro={e}")
        await enviar_texto(chat_id, "Nao consegui buscar os sabores agora. Tente de novo em instantes.")
        return
    if not sabores:
        await enviar_texto(chat_id, "Nenhum pedido registrado ainda.")
        return
    linhas = ["Sabores mais vendidos (acumulado):"]
    for s in sabores:
        linhas.append(f"• {s['sabor']}: {s['quantidade']} unidades")
    await enviar_texto(chat_id, "\n".join(linhas))


async def _enviar_resumo(chat_id: str) -> None:
    try:
        dados = await obter_resumo_mes()
    except Exception as e:
        logger.error(f"Erro ao buscar resumo — chat_id={chat_id} erro={e}")
        await enviar_texto(chat_id, "Nao consegui buscar o resumo agora. Tente de novo em instantes.")
        return
    await enviar_texto(
        chat_id,
        f"Resumo de {dados['mes']}/{dados['ano']}:\n"
        f"Receitas: R${dados['receitas']:.2f}\n"
        f"Despesas: R${dados['despesas']:.2f}\n"
        f"Saldo:    R${dados['saldo']:.2f}"
    )


def _extrair_texto_mensagem(message: dict) -> str | None:
    return (
        message.get("conversation")
        or message.get("extendedTextMessage", {}).get("text")
    )
