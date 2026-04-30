"""
Script one-time para registrar histórico de vendas no Google Sheets.
Lê o log do WhatsApp já filtrado e gravado aqui como dado estruturado.

Uso:
    python registrar_historico.py

Lógica por entrada:
    ja_lancado=False + valor presente  → Lançamentos + Pedidos
    ja_lancado=False + sem valor       → só Pedidos
    ja_lancado=False + sem itens       → só Lançamentos
    ja_lancado=True                    → só Pedidos (evita duplicar)
"""
import asyncio
import sys
from dataclasses import dataclass
from datetime import date

sys.path.insert(0, ".")

from app.integracoes.sheets import adicionar_lancamento, adicionar_pedido, configurar_pedidos
from app.processador.schema import ItemVenda, TipoTransacao, Transacao


@dataclass
class Entrada:
    data: date
    cliente: str
    itens: list[ItemVenda]
    valor: float | None
    ja_lancado: bool  # True = já está em Lançamentos, só precisa ir para Pedidos


def i(*pares) -> list[ItemVenda]:
    return [ItemVenda(descricao=pares[n], quantidade=pares[n + 1]) for n in range(0, len(pares), 2)]


HISTORICO: list[Entrada] = [
    # ── PRÉ-BOT: sem preço → só Pedidos ─────────────────────────────────────────────────────
    Entrada(date(2026, 1, 23), "Maghda",        i("cookie", 5),                                                                                       None,  False),
    Entrada(date(2026, 1, 27), "Ari",           i("kinder", 2, "limão", 1, "nutella", 1),                                                             None,  False),
    Entrada(date(2026, 1, 27), "Paula",         i("kinder", 1, "limão com chocolate branco", 1, "tradicional", 1, "duo com amêndoas", 1),              None,  False),
    Entrada(date(2026, 2, 17), "Arthur",        i("tradicional", 1),                                                                                  None,  False),
    Entrada(date(2026, 2, 17), "Juliane",       i("cookie", 5),                                                                                       None,  False),
    Entrada(date(2026, 2, 17), "Andrea",        i("tradicional", 2, "kinder", 2),                                                                     None,  False),
    Entrada(date(2026, 2, 17), "Paula",         i("nutella com laranja", 2, "kinder", 1, "limão com chocolate branco", 1),                             None,  False),
    Entrada(date(2026, 2, 18), "Helena",        i("kinder", 1),                                                                                       None,  False),
    Entrada(date(2026, 2, 18), "Tati",          i("kinder", 1, "duo com amêndoas", 1, "limão com chocolate branco", 1),                               None,  False),
    Entrada(date(2026, 2, 18), "Ari",           i("limão", 2, "kinder", 1, "nutella com laranja", 1),                                                 None,  False),
    Entrada(date(2026, 2, 19), "Maghda",        i("tradicional", 4, "limão", 1),                                                                      None,  False),
    Entrada(date(2026, 2, 19), "Mari",          i("tradicional", 1, "kinder", 1),                                                                     None,  False),
    Entrada(date(2026, 2, 19), "Brendo",        i("cookie", 1),                                                                                       None,  False),
    Entrada(date(2026, 2, 19), "Paula",         i("kinder", 1, "laranja com nutella", 1, "limão com chocolate branco", 1, "duo com amêndoas", 1),      None,  False),
    Entrada(date(2026, 2, 20), "Samantha",      i("kinder", 1),                                                                                       None,  False),
    Entrada(date(2026, 3,  5), "Paula",         i("limão", 3, "kinder", 3),                                                                           None,  False),
    Entrada(date(2026, 3,  5), "Jana",          i("limão", 1, "kinder", 1, "nutella", 1, "tradicional", 1, "duo com amêndoas", 1),                    None,  False),
    Entrada(date(2026, 3, 12), "Amiga Tati",    i("limão", 3, "nutella", 2),                                                                          None,  False),
    Entrada(date(2026, 3, 12), "Tati",          i("tradicional", 1),                                                                                  None,  False),
    Entrada(date(2026, 3, 13), "Ari",           i("tradicional", 1, "kinder", 1),                                                                     None,  False),
    Entrada(date(2026, 3, 13), "Daia",          i("kinder", 1),                                                                                       None,  False),
    Entrada(date(2026, 3, 17), "Andrea",        i("buenos", 2, "tradicional", 3),                                                                     None,  False),
    Entrada(date(2026, 3, 17), "Maghda",        i("tradicional", 3, "limão", 2),                                                                      None,  False),
    Entrada(date(2026, 3, 17), "Andre",         i("tradicional", 2),                                                                                  None,  False),
    Entrada(date(2026, 3, 17), "Jiane",         i("duo com amêndoas", 1, "kinder", 1),                                                                None,  False),
    Entrada(date(2026, 3, 18), "Ari",           i("cookie", 6),                                                                                       None,  False),
    Entrada(date(2026, 3, 18), "Daia",          i("nutella com laranja", 1),                                                                          None,  False),
    Entrada(date(2026, 3, 25), "Ari",           i("cookie", 4),                                                                                       None,  False),
    Entrada(date(2026, 3, 25), "Mari",          i("limão", 1),                                                                                        None,  False),

    # ── PRÉ-BOT: com preço → Lançamentos + Pedidos ──────────────────────────────────────────
    Entrada(date(2026, 1, 26), "Ari",           i("cookie", 1),                                                                                       10.00, False),

    # ── Misclassificadas como COMPRA pelo bot → corrigir como RECEITA ───────────────────────
    Entrada(date(2026, 3, 29), "Luana",         i("limão", 3, "nutella", 2),                                                                          50.00, False),
    Entrada(date(2026, 3, 29), "Jana",          i("limão", 1, "kinder", 1, "nutella", 1, "tradicional", 1, "duo com amêndoas", 1),                    50.00, False),
    Entrada(date(2026, 3, 29), "Paula",         i("limão", 3, "kinder", 3),                                                                           55.00, False),
    Entrada(date(2026, 4, 29), "Jiane",         i("limão", 1),                                                                                        12.00, False),

    # ── Debi 29/04: bot ativo mas não registrou ──────────────────────────────────────────────
    Entrada(date(2026, 4, 29), "Debi",          i("laranja", 1, "limão", 1),                                                                          24.00, False),

    # ── Corretamente registradas pelo bot: só Pedidos ────────────────────────────────────────
    Entrada(date(2026, 3, 28), "Klaubinho",     i("cookie", 5),                                                                                       50.09, True),
    Entrada(date(2026, 3, 29), "Mari",          i("limão", 1),                                                                                        12.00, True),
    Entrada(date(2026, 3, 29), "Ari",           i("mini cookie", 4),                                                                                  10.00, True),
    Entrada(date(2026, 3, 29), "Daia",          i("nutella com laranja", 1),                                                                          12.00, True),
    Entrada(date(2026, 3, 29), "Ari",           i("mini cookie", 5),                                                                                  25.00, True),
    Entrada(date(2026, 3, 29), "Luana",         i("mini cookie", 5),                                                                                  20.00, True),
    Entrada(date(2026, 3, 29), "Jiane",         i("duo com amêndoas", 1, "kinder", 1),                                                                24.00, True),
    Entrada(date(2026, 3, 29), "Andre",         i("tradicional", 2),                                                                                  20.00, True),
    Entrada(date(2026, 3, 29), "Maghda",        i("tradicional", 3, "limão", 2),                                                                      50.00, True),
    Entrada(date(2026, 3, 29), "Andrea",        i("kinder", 2, "tradicional", 3),                                                                     50.00, True),
    Entrada(date(2026, 3, 29), "Daia",          i("kinder", 1),                                                                                       12.00, True),
    Entrada(date(2026, 3, 29), "Ari",           i("tradicional", 1, "kinder", 1),                                                                     22.00, True),
    Entrada(date(2026, 3, 29), "Paula",         i("tradicional", 1),                                                                                  10.00, True),
    Entrada(date(2026, 3, 29), "Tati",          i("tradicional", 1),                                                                                  10.00, True),
    Entrada(date(2026, 3, 29), "Samantha",      i("kinder", 1),                                                                                       12.00, True),
    Entrada(date(2026, 3, 29), "Paula",         i("kinder", 1, "laranja com nutella", 1, "limão com chocolate branco", 1, "duo com amêndoas", 1),      44.00, True),
    Entrada(date(2026, 3, 29), "Brendo",        i("kinder", 1),                                                                                       12.00, True),
    Entrada(date(2026, 3, 29), "Mari",          i("tradicional", 1, "kinder", 1),                                                                     22.00, True),
    Entrada(date(2026, 3, 29), "Maghda",        i("tradicional", 4, "limão", 1),                                                                      50.00, True),
    Entrada(date(2026, 3, 29), "Ari",           i("limão", 2, "kinder", 1, "nutella com laranja", 1),                                                 44.00, True),
    Entrada(date(2026, 3, 29), "Tati",          i("kinder", 1, "duo com amêndoas", 1, "limão com chocolate branco", 1),                               36.00, True),
    Entrada(date(2026, 3, 29), "Helena",        i("kinder", 1),                                                                                       12.00, True),
    Entrada(date(2026, 3, 29), "Paula",         i("nutella com laranja", 2, "kinder", 1, "limão com chocolate branco", 1),                            44.00, True),
    Entrada(date(2026, 3, 29), "Andrea",        i("tradicional", 2, "kinder", 2),                                                                     44.00, True),
    Entrada(date(2026, 3, 29), "Juliane",       i("cookie", 5),                                                                                       50.00, True),
    Entrada(date(2026, 3, 29), "Arthur",        i("tradicional", 1),                                                                                  10.00, True),
    Entrada(date(2026, 3, 29), "Ari",           i("cookie", 4),                                                                                       44.00, True),
    Entrada(date(2026, 3, 29), "Maghda",        i("cookie", 5),                                                                                       50.00, True),
    Entrada(date(2026, 3, 29), "Paula",         i("cookie", 4),                                                                                       44.00, True),
    Entrada(date(2026, 3, 29), "Klauber",       i("cookie", 24),                                                                                      165.85, True),
    Entrada(date(2026, 3, 29), "Maghda",        i("cookie", 20),                                                                                      160.00, True),
    Entrada(date(2026, 3, 29), "Kézily",        i("cookie", 10),                                                                                      70.00, True),
    Entrada(date(2026, 3, 29), "Ari",           i("cookie", 5),                                                                                       40.00, True),
    Entrada(date(2026, 3, 29), "Becca",         i("cookie", 5),                                                                                       40.00, True),
    Entrada(date(2026, 3, 29), "Juliane",       i("cookie", 4),                                                                                       30.00, True),
    Entrada(date(2026, 3, 29), "Arthur",        i("cookie", 5),                                                                                       40.00, True),
    Entrada(date(2026, 3, 29), "Juliane",       i("cookie", 10),                                                                                      80.00, True),
    Entrada(date(2026, 3, 30), "Maghda",        i("pistache", 1, "tradicional", 2),                                                                   35.00, True),
    Entrada(date(2026, 4,  1), "Paula",         i("pistache", 1, "kinder", 1, "limão com chocolate branco", 1, "tradicional", 1, "nutella", 1),        59.00, True),
    Entrada(date(2026, 4,  1), "Mylena",        i("nutella com laranja", 1),                                                                          12.00, True),
    Entrada(date(2026, 4,  1), "Andrea",        i("kinder", 2, "tradicional", 2),                                                                     48.00, True),
    Entrada(date(2026, 4,  1), "Luana",         i("limão", 3, "laranja", 3),                                                                          30.00, True),
    Entrada(date(2026, 4,  1), "Emilene",       i("tradicional", 2),                                                                                  20.00, True),
    Entrada(date(2026, 4,  1), "Andre",         i("tradicional", 3, "limão", 1),                                                                      45.00, True),
    Entrada(date(2026, 4,  1), "Paula",         i("cookie", 6),                                                                                       40.00, True),
    Entrada(date(2026, 4,  1), "Thiago Marques",i("kinder", 5),                                                                                       65.00, True),
    Entrada(date(2026, 4,  1), "Ari",           i("limão", 1, "laranja", 1, "tradicional", 1, "amêndoas", 1),                                         45.00, True),
    Entrada(date(2026, 4,  2), "Mari",          i("kinder", 1),                                                                                       14.00, True),
    Entrada(date(2026, 4,  2), "Jeane",         i("nutella", 1),                                                                                      12.00, True),
    Entrada(date(2026, 4,  2), "Helena",        i("nutella", 1),                                                                                      12.00, True),
    Entrada(date(2026, 4, 26), "Ari",           i("pistache", 2, "tradicional", 1),                                                                   40.00, True),
    Entrada(date(2026, 4, 28), "Arthur",        i("nutella", 1, "tradicional", 1),                                                                    22.00, True),
    Entrada(date(2026, 4, 29), "Mari",          i("kinder", 1, "pistache", 1),                                                                        29.00, True),
    Entrada(date(2026, 4, 29), "Helena",        i("kinder", 3),                                                                                       42.00, True),
    Entrada(date(2026, 4, 29), "Andrea",        i("tradicional", 2, "kinder", 2),                                                                     48.00, True),
    Entrada(date(2026, 4, 29), "Maghda",        i("tradicional", 2),                                                                                  20.00, True),
    Entrada(date(2026, 4, 29), "Paula",         i("kinder", 1, "limão com chocolate branco", 1, "tradicional", 2, "nutella com laranja", 1, "duo com amêndoas", 1), 40.00, True),
    Entrada(date(2026, 4, 29), "Marlise",       i("duo com amêndoas", 1),                                                                             12.00, True),
    Entrada(date(2026, 4, 29), "Tia Lourdes",   i("tradicional", 4),                                                                                  40.00, True),
    Entrada(date(2026, 4, 29), "Madalene",      i("amêndoas", 1, "tradicional", 2, "limão com chocolate", 1),                                         45.00, True),
]


def _transacao(entrada: Entrada, valor_override: float | None = None) -> Transacao:
    descricao = f"Venda para {entrada.cliente}"
    if entrada.itens:
        descricao += " — " + ", ".join(f"{it.quantidade} {it.descricao}" for it in entrada.itens)
    return Transacao(
        tipo=TipoTransacao.RECEITA,
        descricao=descricao,
        valor=valor_override if valor_override is not None else (entrada.valor or 0.0),
        data=entrada.data,
        confianca=1.0,
        origem="histórico",
        cliente=entrada.cliente,
        itens=entrada.itens,
    )


async def processar(entrada: Entrada, idx: int, total: int) -> None:
    prefixo = f"[{idx:>3}/{total}] {entrada.data.strftime('%d/%m/%Y')} {entrada.cliente:<16}"

    if not entrada.ja_lancado and entrada.valor is not None:
        await adicionar_lancamento(_transacao(entrada))
        print(f"{prefixo} → Lançamentos R${entrada.valor:.2f}")

    if entrada.itens:
        await adicionar_pedido(_transacao(entrada))
        qtd = sum(it.quantidade for it in entrada.itens)
        print(f"{prefixo} → Pedidos {qtd} cookies")
    elif not entrada.ja_lancado and entrada.valor is not None:
        # sem itens, só financeiro — já registrado acima
        pass
    else:
        print(f"{prefixo} → ignorado (sem itens e sem valor)")

    await asyncio.sleep(0.5)  # respeita quota da API Google Sheets


async def main() -> None:
    print("Garantindo aba Pedidos...")
    await configurar_pedidos()

    total = len(HISTORICO)
    print(f"Processando {total} entradas históricas...\n")
    for idx, entrada in enumerate(HISTORICO, 1):
        await processar(entrada, idx, total)

    print(f"\nConcluído! {total} entradas processadas.")
    print("Nota: 4 entradas foram misclassificadas como COMPRA pelo bot (Luana, Jana, Paula, Jiane).")
    print("      Os lançamentos incorretos AINDA estão em Lançamentos — verifique e remova manualmente se necessário.")


if __name__ == "__main__":
    asyncio.run(main())
