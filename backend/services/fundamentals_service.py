"""
fundamentals_service.py — Fundamentos reais (LPA, VPA, ROE, dividendos...) via Yahoo Finance
==============================================================================================

Os fundamentos mudam a cada balanço (3 em 3 meses), então não precisam ser consultados a cada
clique: este módulo guarda o resultado por 6 horas. Se o Yahoo falhar, os valores do
``data/fallback_b3.json`` continuam valendo (marcados como "estimado" no campo
``fonte_fundamentos``).

``extrair_fundamentos`` é pura (recebe o dicionário ``info`` do Yahoo e devolve os campos do app),
o que facilita testá-la e reutilizá-la no script ``scripts/atualizar_fallback.py``.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger("alpharadar.fundamentos")

TTL_SUCESSO = 6 * 3600
TTL_FALHA = 5 * 60
SETORES_FINANCEIROS = {"Bancos", "Seguros", "Serviços financeiros", "Holding financeira", "Bolsa e serviços financeiros"}

_estado: dict[str, Any] = {"t": 0.0, "dados": {}}
_trava = threading.Lock()


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # descarta NaN


def extrair_fundamentos(info: dict[str, Any], tipo: str = "acao", setor: str = "") -> dict[str, Any]:
    """
    Converte o ``info`` do Yahoo nos campos usados pelo motor de valuation.

    Devolve só o que veio com valor confiável; quem chama mescla por cima dos dados de reserva.
    Para FIIs usamos apenas os dividendos dos últimos 12 meses e o beta: LPA/ROE de fundo
    imobiliário não são publicados da mesma forma que os de empresas.
    """
    out: dict[str, Any] = {}
    dpa = _num(info.get("trailingAnnualDividendRate")) or _num(info.get("dividendRate"))
    if dpa is not None and dpa >= 0:
        out["dpa_12m"] = round(dpa, 2)
    beta = _num(info.get("beta"))
    if beta is not None:
        out["beta"] = round(beta, 2)
    if tipo == "fii":
        vpa = _num(info.get("bookValue"))
        if vpa and vpa > 0:
            out["vpa"] = round(vpa, 2)
        return out

    lpa, vpa = _num(info.get("trailingEps")), _num(info.get("bookValue"))
    if lpa is not None:
        out["lpa"] = round(lpa, 2)
        fwd = _num(info.get("forwardEps"))
        if lpa > 0 and fwd is not None:
            out["crescimento_lucro"] = round(max(-0.10, min(0.20, fwd / lpa - 1)), 2)
    if vpa is not None and vpa > 0:
        out["vpa"] = round(vpa, 2)
    payout = _num(info.get("payoutRatio"))
    if payout is not None and payout >= 0:
        out["payout_medio"] = round(min(payout, 1.0) * 100)
    roe = _num(info.get("returnOnEquity"))
    if roe is not None:
        out["roe"] = round(roe * 100, 1)
    pl, pvp = _num(info.get("trailingPE")), _num(info.get("priceToBook"))
    if pl is not None and pl > 0:
        out["pl"] = round(pl, 1)
    if pvp is not None and pvp > 0:
        out["pvp"] = round(pvp, 2)
    # Dívida líquida/EBITDA não se aplica a bancos e seguradoras (o "caixa" deles é o próprio negócio).
    divida, caixa, ebitda = _num(info.get("totalDebt")), _num(info.get("totalCash")), _num(info.get("ebitda"))
    if setor not in SETORES_FINANCEIROS and divida is not None and caixa is not None and ebitda and ebitda > 0:
        out["divida_liquida_ebitda"] = round((divida - caixa) / ebitda, 2)
    return out


def aplicar_fundamentos(ativo: dict[str, Any], campos: dict[str, Any]) -> None:
    """
    Mescla os campos do Yahoo no ativo e recalcula o que deriva deles:
    payout (quando o Yahoo não informa), LPA/ROE de FIIs e P/L e P/VP com a cotação atual.
    """
    ativo.update(campos)
    dpa = ativo.get("dpa_12m") or 0
    if ativo.get("tipo") == "fii":
        if dpa:
            ativo["lpa"], ativo["payout_medio"] = round(dpa / 0.95, 2), 95  # FIIs distribuem ~95% do resultado
        if dpa and ativo.get("vpa"):
            ativo["roe"] = round(dpa / ativo["vpa"] * 100, 1)
    elif "payout_medio" not in campos and (ativo.get("lpa") or 0) > 0:
        ativo["payout_medio"] = round(min(dpa / ativo["lpa"], 1.0) * 100)
    cot = ativo.get("cotacao") or 0
    lpa, vpa = ativo.get("lpa") or 0, ativo.get("vpa") or 0
    ativo["pl"] = round(cot / lpa, 1) if cot and lpa > 0 else None
    ativo["pvp"] = round(cot / vpa, 2) if cot and vpa > 0 else None
    ativo["fonte_fundamentos"] = "ao_vivo"


def _info(simbolo: str) -> dict[str, Any]:
    import yfinance as yf

    return yf.Ticker(simbolo).info or {}


def baixar_fundamentos(ativos: list[dict[str, Any]], timeout: float = 40.0) -> dict[str, dict[str, Any]]:
    """Consulta o Yahoo em paralelo (8 threads) e devolve ``{ticker: campos}``. Falhas individuais são ignoradas."""
    from services import market_service

    resultado: dict[str, dict[str, Any]] = {}
    pool = ThreadPoolExecutor(max_workers=8)
    futuros = {pool.submit(_info, market_service.simbolo_yahoo(a)): a for a in ativos}
    try:
        for fut in as_completed(futuros, timeout=timeout):
            a = futuros[fut]
            try:
                campos = extrair_fundamentos(fut.result(), a.get("tipo", "acao"), a.get("setor", ""))
                if campos:
                    resultado[a["ticker"]] = campos
            except Exception as erro:  # noqa: BLE001
                logger.debug("Fundamentos de %s indisponíveis: %s", a["ticker"], type(erro).__name__)
    except TimeoutError:
        logger.warning("Fundamentos: tempo esgotado; usando o que chegou (%d de %d)", len(resultado), len(ativos))
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    return resultado


def fundamentos_ao_vivo(ativos: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Fundamentos com cache de 6 h (5 min se tudo falhou, para tentar de novo logo)."""
    agora = time.time()
    with _trava:
        idade = agora - _estado["t"]
        if _estado["dados"] and idade < TTL_SUCESSO:
            return _estado["dados"]
        if not _estado["dados"] and _estado["t"] and idade < TTL_FALHA:
            return {}
    dados = baixar_fundamentos(ativos)
    with _trava:
        _estado["t"], _estado["dados"] = time.time(), dados
    return dados
