"""
valuation.py — Motor de Valuation do AlphaRadar B3
====================================================

Este módulo implementa, do zero e em Python puro, as fórmulas clássicas de
avaliação de ações que são de DOMÍNIO PÚBLICO (Art. 8º, I, da Lei 9.610/98:
"ideias, métodos e conceitos matemáticos" não são protegidos por direito autoral).

Fórmulas implementadas e suas origens na literatura:

1. Preço Justo de Graham  -> Benjamin Graham, "The Intelligent Investor" (1949)
       Preço Justo = √(22,5 × LPA × VPA)
   O número 22,5 vem de P/L máximo (15) × P/VP máximo (1,5).

2. Preço-Teto de Bazin (histórico) -> Décio Bazin, "Faça Fortuna com Ações" (1992)
       Preço-Teto = DPA dos últimos 12 meses ÷ yield mínimo (padrão 6%)

3. Preço-Teto Projetivo -> extensão "olhando para frente" do método de Bazin
       DPA Projetado = LPA × (1 + g) × Payout
       Preço-Teto Projetivo = DPA Projetado ÷ yield desejado

4. Margem de Segurança -> conceito de Graham
       Margem (%) = (Preço-Teto − Cotação) ÷ Cotação × 100

5. Score Alpha (0 a 100) -> métrica AUTORAL deste projeto: 5 pilares de 20 pontos.

Glossário rápido:
    LPA  = Lucro por Ação (lucro líquido ÷ número de ações)
    VPA  = Valor Patrimonial por Ação (patrimônio líquido ÷ número de ações)
    DPA  = Dividendos (proventos) por Ação
    g    = taxa de crescimento esperada do lucro (ex.: 0,05 = 5%)
    Payout = % do lucro que a empresa distribui aos acionistas
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Constantes de negócio (centralizadas para facilitar ajustes e testes)
# ---------------------------------------------------------------------------

CONSTANTE_GRAHAM: float = 22.5      # 15 (P/L máx.) × 1,5 (P/VP máx.)
YIELD_MINIMO_BAZIN: float = 0.06    # 6% ao ano — padrão clássico de Bazin
# FIIs distribuem ~95% do resultado e quase não reinvestem para crescer, por
# isso o mercado costuma exigir deles um yield maior que o de ações.
YIELD_REFERENCIA_FII: float = 0.08  # 8% ao ano


def yield_padrao(ativo: dict[str, Any]) -> float:
    """Yield exigido padrão: 6% para ações (Bazin) e 8% para FIIs."""
    return YIELD_REFERENCIA_FII if ativo.get("tipo") == "fii" else YIELD_MINIMO_BAZIN
PONTOS_POR_PILAR: float = 20.0      # 5 pilares × 20 = 100 pontos


# ---------------------------------------------------------------------------
# 1. Fórmulas individuais
# ---------------------------------------------------------------------------

def preco_justo_graham(lpa: float, vpa: float) -> float | None:
    """
    Calcula o Preço Justo de Graham: √(22,5 × LPA × VPA).

    Retorna ``None`` quando LPA ou VPA são negativos/zero, porque a raiz
    quadrada de um número negativo não existe nos reais — e, conceitualmente,
    Graham não se aplica a empresas com prejuízo ou patrimônio negativo.

    >>> round(preco_justo_graham(2.0, 10.0), 2)
    21.21
    """
    if lpa is None or vpa is None or lpa <= 0 or vpa <= 0:
        return None
    return math.sqrt(CONSTANTE_GRAHAM * lpa * vpa)


def preco_teto_bazin_historico(dpa_12m: float, yield_min: float = YIELD_MINIMO_BAZIN) -> float | None:
    """
    Preço-Teto de Bazin "pelo retrovisor": usa os dividendos já pagos nos
    últimos 12 meses.

    Interpretação: "qual o preço máximo que posso pagar para receber, no
    mínimo, ``yield_min`` de dividendos por ano?"

    >>> preco_teto_bazin_historico(1.2, 0.06)
    20.0
    """
    if dpa_12m is None or dpa_12m <= 0 or yield_min <= 0:
        return None
    return dpa_12m / yield_min


def dpa_projetado(lpa: float, crescimento_g: float, payout_pct: float) -> float:
    """
    Estima o dividendo por ação dos PRÓXIMOS 12 meses.

    DPA Projetado = LPA × (1 + g) × (Payout ÷ 100)

    ``payout_pct`` é recebido em pontos percentuais (ex.: 50 = 50%).
    """
    if lpa is None or lpa <= 0 or payout_pct is None or payout_pct <= 0:
        return 0.0
    return lpa * (1 + crescimento_g) * (payout_pct / 100)


def preco_teto_projetivo(
    lpa: float,
    crescimento_g: float,
    payout_pct: float,
    yield_desejado: float,
) -> float | None:
    """
    Preço-Teto Projetivo "pelo para-brisa": em vez do dividendo passado,
    usa o dividendo que a empresa DEVE pagar se o lucro crescer ``g`` e o
    payout se mantiver.

    Preço-Teto Projetivo = (LPA × (1 + g) × Payout%) ÷ yield desejado

    >>> round(preco_teto_projetivo(4.0, 0.05, 50, 0.06), 2)
    35.0
    """
    if yield_desejado is None or yield_desejado <= 0:
        return None
    dpa = dpa_projetado(lpa, crescimento_g, payout_pct)
    if dpa <= 0:
        return None
    return dpa / yield_desejado


def margem_seguranca(preco_teto: float | None, cotacao_atual: float) -> float | None:
    """
    Margem de Segurança em %: quanto o preço-teto está acima (positivo =
    desconto/potencial) ou abaixo (negativo = ação "cara") da cotação.

    >>> margem_seguranca(30.0, 25.0)
    20.0
    """
    if preco_teto is None or cotacao_atual is None or cotacao_atual <= 0:
        return None
    return (preco_teto - cotacao_atual) / cotacao_atual * 100


def dividend_yield(dpa: float, cotacao: float) -> float:
    """Dividend Yield em % = DPA ÷ cotação × 100."""
    if not cotacao or cotacao <= 0 or not dpa:
        return 0.0
    return dpa / cotacao * 100


# ---------------------------------------------------------------------------
# 2. Score Alpha (0 a 100) — métrica autoral e AUDITÁVEL
# ---------------------------------------------------------------------------

@dataclass
class Pilar:
    """Um dos 5 pilares do Score Alpha, com explicação legível por humanos."""

    nome: str
    pontos: float
    maximo: float
    valor_base: float | None   # o indicador bruto que gerou a nota
    explicacao: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "pontos": round(self.pontos, 1),
            "maximo": self.maximo,
            "valor_base": None if self.valor_base is None else round(self.valor_base, 2),
            "explicacao": self.explicacao,
        }


@dataclass
class ScoreAlpha:
    total: float
    classificacao: str
    pilares: list[Pilar] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": round(self.total, 1),
            "classificacao": self.classificacao,
            "pilares": [p.to_dict() for p in self.pilares],
        }


def _escala_linear(valor: float, pior: float, melhor: float, maximo: float = PONTOS_POR_PILAR) -> float:
    """
    Converte um indicador em pontos usando interpolação linear.

    - ``valor`` igual (ou pior) que ``pior``  -> 0 pontos
    - ``valor`` igual (ou melhor) que ``melhor`` -> ``maximo`` pontos
    Funciona também quando "menor é melhor" (basta passar pior > melhor).
    """
    if pior == melhor:
        return maximo
    proporcao = (valor - pior) / (melhor - pior)
    proporcao = max(0.0, min(1.0, proporcao))  # "clamp" entre 0 e 1
    return proporcao * maximo


def classificar_score(total: float) -> str:
    """Traduz a nota numérica em um rótulo amigável (fins educativos)."""
    if total >= 80:
        return "Excelente"
    if total >= 65:
        return "Bom"
    if total >= 50:
        return "Neutro"
    if total >= 35:
        return "Atenção"
    return "Fraco"


def calcular_score_alpha(ativo: dict[str, Any], sentimento_noticias: float = 0.0) -> ScoreAlpha:
    """
    Calcula o Score Alpha (0–100) de uma ação ou FII.

    Parâmetros
    ----------
    ativo : dict
        Precisa conter: ``cotacao``, ``lpa``, ``vpa``, ``payout_medio``,
        ``crescimento_lucro``, ``roe``, ``divida_liquida_ebitda`` (pode ser None)
        e opcionalmente ``yield_desejado``.
    sentimento_noticias : float
        Média do sentimento das notícias da semana, de -1 (muito negativo)
        a +1 (muito positivo). Calculado em ``services/news_service.py``.

    Os 5 pilares (20 pontos cada):
        1. Margem vs. Preço-Teto Projetivo  (-20% → 0 pts ... +30% → 20 pts)
        2. Dividend Yield Projetado         (0% → 0 pts ... 10% → 20 pts)
        3. Rentabilidade (ROE)              (0% → 0 pts ... 20% → 20 pts)
        4. Endividamento (Dív.Líq./EBITDA)  (4x → 0 pts ... 0x → 20 pts)
        5. Sentimento das notícias          (-1 → 0 pts ... +1 → 20 pts)
    """
    cotacao = float(ativo.get("cotacao") or 0)
    yield_desejado = float(ativo.get("yield_desejado") or yield_padrao(ativo))
    teto_proj = preco_teto_projetivo(
        ativo.get("lpa") or 0,
        ativo.get("crescimento_lucro") or 0,
        ativo.get("payout_medio") or 0,
        yield_desejado,
    )
    pilares: list[Pilar] = []

    # --- Pilar 1: Margem de segurança frente ao Preço-Teto Projetivo ---
    margem = margem_seguranca(teto_proj, cotacao)
    if margem is None:
        pts, expl = 0.0, "Sem dividendos projetados: não há preço-teto para comparar."
    else:
        pts = _escala_linear(margem, pior=-20, melhor=30)
        situacao = "abaixo" if margem >= 0 else "acima"
        expl = f"Cotação {abs(margem):.1f}% {situacao} do Preço-Teto Projetivo."
    pilares.append(Pilar("Margem vs. Preço-Teto", pts, PONTOS_POR_PILAR, margem, expl))

    # --- Pilar 2: Dividend Yield projetado ---
    dy_proj = dividend_yield(
        dpa_projetado(ativo.get("lpa") or 0, ativo.get("crescimento_lucro") or 0, ativo.get("payout_medio") or 0),
        cotacao,
    )
    pilares.append(Pilar(
        "Dividend Yield Projetado",
        _escala_linear(dy_proj, pior=0, melhor=10),
        PONTOS_POR_PILAR,
        dy_proj,
        f"Rendimento projetado de {dy_proj:.1f}% ao ano (10% ou mais = nota máxima).",
    ))

    # --- Pilar 3: Rentabilidade (ROE) ---
    roe = float(ativo.get("roe") or 0)
    pilares.append(Pilar(
        "Rentabilidade (ROE)",
        _escala_linear(roe, pior=0, melhor=20),
        PONTOS_POR_PILAR,
        roe,
        f"ROE de {roe:.1f}% (20% ou mais = nota máxima).",
    ))

    # --- Pilar 4: Endividamento ---
    dl_ebitda = ativo.get("divida_liquida_ebitda")
    if dl_ebitda is None:
        # Bancos, seguradoras e FIIs não usam Dívida/EBITDA: nota neutra (70%).
        pts = PONTOS_POR_PILAR * 0.7
        expl = "Indicador não se aplica a este tipo de ativo (banco, seguradora ou FII): nota neutra."
    else:
        pts = _escala_linear(float(dl_ebitda), pior=4.0, melhor=0.0)
        expl = f"Dívida Líquida/EBITDA de {float(dl_ebitda):.1f}x (caixa líquido = nota máxima; 4x ou mais = zero)."
    pilares.append(Pilar("Endividamento", pts, PONTOS_POR_PILAR, dl_ebitda, expl))

    # --- Pilar 5: Sentimento das notícias ---
    sent = max(-1.0, min(1.0, float(sentimento_noticias)))
    rotulo = "positivo" if sent > 0.15 else "negativo" if sent < -0.15 else "neutro"
    pilares.append(Pilar(
        "Sentimento de Notícias",
        _escala_linear(sent, pior=-1, melhor=1),
        PONTOS_POR_PILAR,
        sent,
        f"Fluxo de notícias da semana {rotulo} (índice {sent:+.2f}).",
    ))

    total = sum(p.pontos for p in pilares)
    return ScoreAlpha(total=total, classificacao=classificar_score(total), pilares=pilares)


# ---------------------------------------------------------------------------
# 3. Função "tudo em um": usada pelas rotas da API
# ---------------------------------------------------------------------------

def avaliar_ativo(
    ativo: dict[str, Any],
    yield_desejado: float | None = None,
    crescimento_g: float | None = None,
    payout_pct: float | None = None,
    sentimento_noticias: float = 0.0,
) -> dict[str, Any]:
    """
    Aplica TODAS as fórmulas a um ativo e devolve um dicionário pronto para
    virar JSON. Os parâmetros opcionais permitem que o usuário sobrescreva
    as premissas pelos sliders do frontend (simulação "e se...?").
    """
    y = yield_desejado if yield_desejado is not None else yield_padrao(ativo)
    g = crescimento_g if crescimento_g is not None else float(ativo.get("crescimento_lucro") or 0)
    payout = payout_pct if payout_pct is not None else float(ativo.get("payout_medio") or 0)
    cotacao = float(ativo.get("cotacao") or 0)
    lpa = float(ativo.get("lpa") or 0)
    vpa = float(ativo.get("vpa") or 0)
    dpa_12m = float(ativo.get("dpa_12m") or 0)

    # Graham foi pensado para EMPRESAS; para FIIs (fundos) a fórmula não se aplica.
    graham = None if ativo.get("tipo") == "fii" else preco_justo_graham(lpa, vpa)
    bazin = preco_teto_bazin_historico(dpa_12m, y)
    projetivo = preco_teto_projetivo(lpa, g, payout, y)
    dpa_proj = dpa_projetado(lpa, g, payout)

    # Para o score usamos as MESMAS premissas escolhidas pelo usuário.
    ativo_sim = {**ativo, "crescimento_lucro": g, "payout_medio": payout, "yield_desejado": y}
    score = calcular_score_alpha(ativo_sim, sentimento_noticias)

    def r(v: float | None) -> float | None:
        return None if v is None else round(v, 2)

    return {
        "ticker": ativo.get("ticker"),
        "cotacao": r(cotacao),
        "premissas": {"yield_desejado": y, "crescimento_g": g, "payout_pct": payout},
        "preco_justo_graham": r(graham),
        "preco_teto_bazin": r(bazin),
        "preco_teto_projetivo": r(projetivo),
        "margem_graham": r(margem_seguranca(graham, cotacao)),
        "margem_bazin": r(margem_seguranca(bazin, cotacao)),
        "margem_projetiva": r(margem_seguranca(projetivo, cotacao)),
        "dpa_12m": r(dpa_12m),
        "dpa_projetado": r(dpa_proj),
        "dy_atual": r(dividend_yield(dpa_12m, cotacao)),
        "dy_projetado": r(dividend_yield(dpa_proj, cotacao)),
        "score": score.to_dict(),
    }


if __name__ == "__main__":
    # Execute "python -m engine.valuation" para rodar os exemplos (doctests).
    import doctest

    print(doctest.testmod())
