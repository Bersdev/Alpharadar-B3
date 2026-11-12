"""
fixed_income.py — Simulador de Renda Fixa do AlphaRadar B3
============================================================

Compara, mês a mês, quanto rende o mesmo dinheiro aplicado em:

    • LCI  (Letra de Crédito Imobiliário)  -> ISENTA de IR para pessoa física
    • LCA  (Letra de Crédito do Agronegócio) -> ISENTA de IR para pessoa física
    • CDB  (Certificado de Depósito Bancário) -> IR regressivo
    • Tesouro Selic                           -> IR regressivo + custódia B3
    • Dividendos de FII/ações reinvestidos    -> dividendos isentos para PF

Tabela regressiva de Imposto de Renda (Lei 11.033/2004), sobre o LUCRO:
    até 180 dias ........ 22,5%
    181 a 360 dias ...... 20,0%
    361 a 720 dias ...... 17,5%
    acima de 720 dias ... 15,0%

"Gross-up" tributário: qual taxa um CDB precisa pagar para empatar com uma
LCI/LCA isenta?

    Taxa CDB Equivalente = Taxa LCI ÷ (1 − alíquota de IR)

Exemplo: LCI a 90% do CDI, prazo de 2 anos (alíquota 15%)
         -> 90 ÷ 0,85 = 105,9% do CDI. Um CDB só "ganha" se pagar mais que isso.

Simplificações assumidas (documentadas de propósito, para estudo):
    - Mês comercial = 30 dias corridos; ano = 12 meses.
    - CDI e Selic constantes durante o período simulado.
    - IOF (só incide em resgates com menos de 30 dias) é ignorado.
    - Custódia do Tesouro: 0,20% a.a. sobre todo o saldo (a isenção até
      R$ 10 mil do Tesouro Selic não é modelada).
    - Dividendos: cota com preço constante, dividendos reinvestidos todo mês.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

DIAS_POR_MES: int = 30
TAXA_CUSTODIA_TESOURO_AA: float = 0.0020  # 0,20% ao ano (B3)

# (limite superior em dias, alíquota) — percorrida em ordem
TABELA_IR_REGRESSIVA: list[tuple[int, float]] = [
    (180, 0.225),
    (360, 0.200),
    (720, 0.175),
]
ALIQUOTA_IR_LONGO_PRAZO: float = 0.15


# ---------------------------------------------------------------------------
# Funções básicas
# ---------------------------------------------------------------------------

def aliquota_ir(dias: int) -> float:
    """
    Retorna a alíquota de IR regressiva para um investimento mantido por
    ``dias`` dias corridos.

    >>> aliquota_ir(100), aliquota_ir(200), aliquota_ir(500), aliquota_ir(800)
    (0.225, 0.2, 0.175, 0.15)
    """
    for limite, aliquota in TABELA_IR_REGRESSIVA:
        if dias <= limite:
            return aliquota
    return ALIQUOTA_IR_LONGO_PRAZO


def taxa_cdb_equivalente(taxa_isenta_pct_cdi: float, dias: int) -> float:
    """
    Gross-up: converte a taxa de uma LCI/LCA (isenta) na taxa de CDB
    (tributado) que entregaria o MESMO rendimento líquido.

    >>> round(taxa_cdb_equivalente(90, 800), 2)
    105.88
    """
    return taxa_isenta_pct_cdi / (1 - aliquota_ir(dias))


def taxa_isenta_equivalente(taxa_cdb_pct_cdi: float, dias: int) -> float:
    """Caminho inverso: quanto uma LCI/LCA precisa pagar para empatar com um CDB."""
    return taxa_cdb_pct_cdi * (1 - aliquota_ir(dias))


def _br(valor: float, casas: int = 1) -> str:
    """Formata número no padrão brasileiro (vírgula decimal): 17.5 -> '17,5'."""
    return f"{valor:.{casas}f}".replace(".", ",")


def anual_para_mensal(taxa_anual: float) -> float:
    """Converte taxa anual efetiva (ex.: 0,1065) em taxa mensal equivalente (juros compostos)."""
    return (1 + taxa_anual) ** (1 / 12) - 1


# ---------------------------------------------------------------------------
# Motor de simulação mês a mês (com pandas)
# ---------------------------------------------------------------------------

@dataclass
class ParametrosSimulacao:
    valor_inicial: float = 10_000.0
    aporte_mensal: float = 0.0
    meses: int = 24
    cdi_anual: float = 0.1365         # 13,65% a.a.
    selic_anual: float = 0.1375       # 13,75% a.a.
    taxa_lci_pct_cdi: float = 92.0    # LCI a 92% do CDI
    taxa_lca_pct_cdi: float = 90.0    # LCA a 90% do CDI
    taxa_cdb_pct_cdi: float = 105.0   # CDB a 105% do CDI
    dy_dividendos_anual: float = 0.11 # DY de 11% a.a. (ex.: FII de tijolo)


def _curva_tributada(
    aportes: np.ndarray,
    taxa_mensal: float,
    isento: bool,
    custodia_anual: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Calcula, para cada mês ``m``, o saldo BRUTO e o saldo LÍQUIDO (se resgatado
    naquele mês) de uma série de aportes.

    Cada aporte é tratado como um "lote" independente, porque o IR regressivo
    depende de há quanto tempo AQUELE dinheiro está aplicado — exatamente como
    funciona na vida real (o banco aplica a tabela por aplicação).
    """
    n = len(aportes)
    taxa_liq_custodia = (1 + taxa_mensal) * (1 - custodia_anual / 12) - 1
    # Versão vetorizada (numpy): a matriz tem uma linha por mês de resgate (m) e uma coluna por lote (i).
    # O loop duplo em Python custava ~0,5 s para 360 meses; como a rota é pública, isso era um vetor de
    # negação de serviço (poucos pedidos seguidos saturavam a CPU).
    mes = np.arange(n)[:, None]
    lote = np.arange(n)[None, :]
    idade = mes - lote                                  # meses que o lote i está aplicado no mês m
    existe = (idade >= 0) & (aportes[None, :] != 0)     # só lotes já feitos e com valor
    idade_ok = np.where(existe, idade, 0)
    valor = np.where(existe, aportes[None, :] * (1 + taxa_liq_custodia) ** idade_ok, 0.0)
    bruto = valor.sum(axis=1)
    if isento:
        return bruto, bruto.copy()
    lucro = np.where(existe, valor - aportes[None, :], 0.0)
    dias = idade_ok * DIAS_POR_MES
    aliquota = np.select([dias <= limite for limite, _ in TABELA_IR_REGRESSIVA],
                         [taxa for _, taxa in TABELA_IR_REGRESSIVA], default=ALIQUOTA_IR_LONGO_PRAZO)
    imposto = np.where(lucro > 0, lucro * aliquota, 0.0)
    return bruto, (valor - imposto).sum(axis=1)


def simular_renda_fixa(p: ParametrosSimulacao) -> dict[str, Any]:
    """
    Gera a tabela mês a mês (pandas DataFrame) comparando os 5 investimentos
    e um resumo final pronto para o frontend.
    """
    meses = max(1, int(p.meses))
    # Vetor de aportes: mês 0 = valor inicial, meses seguintes = aporte mensal.
    # O último aporte acontece no mês "meses-1"; o mês "meses" é o resgate.
    aportes = np.zeros(meses + 1)
    aportes[0] = p.valor_inicial
    aportes[1:meses] = p.aporte_mensal

    cdi_m = anual_para_mensal(p.cdi_anual)
    selic_m = anual_para_mensal(p.selic_anual)

    # Taxas mensais de cada produto (% do CDI aplicado sobre a taxa anual)
    taxa = {
        "LCI": anual_para_mensal(p.cdi_anual * p.taxa_lci_pct_cdi / 100),
        "LCA": anual_para_mensal(p.cdi_anual * p.taxa_lca_pct_cdi / 100),
        "CDB": anual_para_mensal(p.cdi_anual * p.taxa_cdb_pct_cdi / 100),
    }

    _, lci = _curva_tributada(aportes, taxa["LCI"], isento=True)
    _, lca = _curva_tributada(aportes, taxa["LCA"], isento=True)
    cdb_bruto, cdb = _curva_tributada(aportes, taxa["CDB"], isento=False)
    _, tesouro = _curva_tributada(aportes, selic_m, isento=False, custodia_anual=TAXA_CUSTODIA_TESOURO_AA)
    # Dividendos isentos reinvestidos: crescimento composto pelo DY mensal.
    _, dividendos = _curva_tributada(aportes, anual_para_mensal(p.dy_dividendos_anual), isento=True)

    investido = np.cumsum(aportes)

    df = pd.DataFrame({
        "mes": np.arange(meses + 1),
        "investido": investido,
        "lci": lci,
        "lca": lca,
        "cdb_bruto": cdb_bruto,
        "cdb_liquido": cdb,
        "tesouro_selic_liquido": tesouro,
        "dividendos_reinvestidos": dividendos,
    }).round(2)

    final = df.iloc[-1]
    dias = meses * DIAS_POR_MES
    aliquota = aliquota_ir(dias)
    total_investido = float(final["investido"])

    def resumo(nome: str, coluna: str, taxa_desc: str, isento: bool) -> dict[str, Any]:
        valor_final = float(final[coluna])
        lucro = valor_final - total_investido
        return {
            "produto": nome,
            "taxa": taxa_desc,
            "isento_ir": isento,
            "valor_final_liquido": round(valor_final, 2),
            "lucro_liquido": round(lucro, 2),
            "rentabilidade_pct": round(lucro / total_investido * 100, 2) if total_investido else 0.0,
        }

    produtos = [
        resumo("LCI", "lci", f"{p.taxa_lci_pct_cdi:.0f}% do CDI", True),
        resumo("LCA", "lca", f"{p.taxa_lca_pct_cdi:.0f}% do CDI", True),
        resumo("CDB", "cdb_liquido", f"{p.taxa_cdb_pct_cdi:.0f}% do CDI", False),
        resumo("Tesouro Selic", "tesouro_selic_liquido", f"Selic {_br(p.selic_anual * 100, 2)}% a.a.", False),
        resumo("Dividendos (FII/Ações)", "dividendos_reinvestidos", f"DY {_br(p.dy_dividendos_anual * 100)}% a.a.", True),
    ]
    melhor = max(produtos, key=lambda x: x["valor_final_liquido"])

    # Quanto de IR a LCI "economiza" frente a um CDB com a MESMA taxa bruta.
    _, cdb_mesma_taxa = _curva_tributada(aportes, taxa["LCI"], isento=False)
    economia_ir_lci = float(lci[-1] - cdb_mesma_taxa[-1])

    return {
        "parametros": p.__dict__,
        "prazo_dias": dias,
        "aliquota_ir_prazo": aliquota,
        "gross_up": {
            "lci_cdb_equivalente_pct_cdi": round(taxa_cdb_equivalente(p.taxa_lci_pct_cdi, dias), 2),
            "lca_cdb_equivalente_pct_cdi": round(taxa_cdb_equivalente(p.taxa_lca_pct_cdi, dias), 2),
            "cdb_lci_equivalente_pct_cdi": round(taxa_isenta_equivalente(p.taxa_cdb_pct_cdi, dias), 2),
            "explicacao": (
                f"Com prazo de {dias} dias a alíquota de IR é {_br(aliquota * 100)}%. "
                f"Uma LCI a {p.taxa_lci_pct_cdi:.0f}% do CDI equivale a um CDB a "
                f"{_br(taxa_cdb_equivalente(p.taxa_lci_pct_cdi, dias))}% do CDI."
            ),
        },
        "economia_ir_lci": round(economia_ir_lci, 2),
        "total_investido": round(total_investido, 2),
        "produtos": produtos,
        "melhor_opcao": melhor["produto"],
        "curva_mensal": df.to_dict(orient="records"),
        "taxas_mensais": {k: round(v * 100, 4) for k, v in {**taxa, "CDI": cdi_m, "Selic": selic_m}.items()},
    }


IR_RETIDO_DIVIDENDOS_EUA: float = 0.30  # retenção na fonte para investidor brasileiro


def premio_de_risco(
    dy_projetado_pct: float, taxa_lci_pct_cdi: float, cdi_anual: float, mercado: str = "B3"
) -> dict[str, Any]:
    """
    Índice de Prêmio de Risco: o dividend yield de uma ação/FII compensa o
    risco de renda variável frente a uma LCI (isenta e segura)?

    Prêmio (p.p.) = DY líquido projetado − rendimento anual da LCI

    Dividendos da B3 são isentos para pessoa física; os dos EUA sofrem 30% de
    IR retido na fonte, então comparamos o DY já líquido desse imposto.
    """
    if mercado == "EUA":
        dy_projetado_pct = dy_projetado_pct * (1 - IR_RETIDO_DIVIDENDOS_EUA)
    rendimento_lci = cdi_anual * 100 * taxa_lci_pct_cdi / 100
    premio = dy_projetado_pct - rendimento_lci
    if premio >= 2:
        leitura = "Prêmio atrativo: o ativo paga bem mais que a LCI."
    elif premio >= 0:
        leitura = "Prêmio apertado: paga pouco a mais que a LCI para correr risco de bolsa."
    else:
        leitura = "Prêmio negativo: a LCI isenta rende mais que os dividendos projetados."
    return {
        "dy_projetado_pct": round(dy_projetado_pct, 2),
        "rendimento_lci_pct": round(rendimento_lci, 2),
        "premio_pp": round(premio, 2),
        "leitura": leitura,
    }


if __name__ == "__main__":
    import doctest

    print(doctest.testmod())
    r = simular_renda_fixa(ParametrosSimulacao())
    print(r["gross_up"]["explicacao"])
    for prod in r["produtos"]:
        print(prod)
