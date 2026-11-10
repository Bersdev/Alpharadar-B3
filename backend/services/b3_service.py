"""
b3_service.py — Cotações, histórico e dividendos da B3
========================================================

Fontes de dados (em ordem de tentativa):
    1. yfinance  -> gratuito, sem chave. Tickers da B3 levam o sufixo ".SA"
                    (ex.: PETR4 -> "PETR4.SA").
    2. brapi.dev -> API brasileira. Alguns tickers funcionam sem token;
                    defina BRAPI_TOKEN no .env para liberar todos.

Todas as funções deste módulo PODEM lançar exceção. Isso é proposital: a
decisão de "cair no fallback" fica centralizada no ``market_service.py``,
o que deixa cada camada com uma responsabilidade só (princípio SRP).
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger("alpharadar.b3")

TIMEOUT_YFINANCE = 12  # segundos — evita que a API "trave" esperando o Yahoo
URL_BRAPI = "https://brapi.dev/api/quote/{tickers}"

# Índices e moedas no Yahoo Finance
SIMBOLOS_MACRO: dict[str, str] = {
    "ibovespa": "^BVSP",
    "dolar": "BRL=X",
    "sp500": "^GSPC",
    "petroleo_brent": "BZ=F",
}

_executor = ThreadPoolExecutor(max_workers=4)


def para_yahoo(ticker: str) -> str:
    """Converte 'PETR4' em 'PETR4.SA' (padrão do Yahoo para a B3)."""
    return ticker if ticker.endswith(".SA") or ticker.startswith("^") or "=" in ticker else f"{ticker}.SA"


def _com_timeout(funcao, *args, timeout: float = TIMEOUT_YFINANCE):
    """Executa ``funcao`` em outra thread e desiste após ``timeout`` segundos."""
    futuro = _executor.submit(funcao, *args)
    try:
        return futuro.result(timeout=timeout)
    except FuturesTimeout as erro:
        raise TimeoutError(f"{funcao.__name__} excedeu {timeout}s") from erro


# ---------------------------------------------------------------------------
# yfinance
# ---------------------------------------------------------------------------

def _baixar_ultimos_fechamentos(simbolos: list[str]) -> pd.DataFrame:
    import yfinance as yf  # import local: o backend sobe mesmo sem yfinance instalado

    dados = yf.download(
        tickers=" ".join(simbolos),
        period="5d",
        interval="1d",
        progress=False,
        auto_adjust=False,
        threads=True,
        group_by="column",
    )
    if dados is None or dados.empty:
        raise ValueError("yfinance retornou tabela vazia")
    fechamentos = dados["Close"]
    if isinstance(fechamentos, pd.Series):          # um único ticker
        fechamentos = fechamentos.to_frame(simbolos[0])
    return fechamentos


def cotacoes_yfinance(tickers: list[str], simbolos_por_ticker: dict[str, str] | None = None) -> dict[str, dict[str, float]]:
    """
    Busca a última cotação e a variação do dia para vários tickers de uma vez.

    ``simbolos_por_ticker`` informa o símbolo no Yahoo quando ele não é o padrão
    da B3 (ex.: ações dos EUA: {"NVDA": "NVDA"}; sem ele, "NVDA" viraria "NVDA.SA").

    Retorna ``{"PETR4": {"cotacao": 31.4, "variacao_dia": -0.63}, ...}``.
    Tickers sem dados são simplesmente omitidos.
    """
    mapa = simbolos_por_ticker or {}
    simbolos = [mapa.get(t) or para_yahoo(t) for t in tickers]
    fechamentos = _com_timeout(_baixar_ultimos_fechamentos, simbolos)

    resultado: dict[str, dict[str, float]] = {}
    for ticker, simbolo in zip(tickers, simbolos):
        if simbolo not in fechamentos.columns:
            continue
        serie = fechamentos[simbolo].dropna()
        if len(serie) == 0:
            continue
        ultimo = float(serie.iloc[-1])
        anterior = float(serie.iloc[-2]) if len(serie) >= 2 else ultimo
        variacao = (ultimo / anterior - 1) * 100 if anterior else 0.0
        resultado[ticker] = {"cotacao": round(ultimo, 2), "variacao_dia": round(variacao, 2)}
    return resultado


def macro_yfinance() -> dict[str, float]:
    """Ibovespa, dólar, S&P 500 e petróleo Brent via yfinance."""
    nomes = list(SIMBOLOS_MACRO.keys())
    cot = cotacoes_yfinance([SIMBOLOS_MACRO[n] for n in nomes])
    resultado: dict[str, float] = {}
    for nome in nomes:
        dado = cot.get(SIMBOLOS_MACRO[nome])
        if dado:
            resultado[nome] = dado["cotacao"]
            resultado[f"{nome}_var"] = dado["variacao_dia"]
    return resultado


def _historico(ticker: str, periodo: str, simbolo: str | None = None) -> tuple[pd.Series, pd.Series]:
    import yfinance as yf

    papel = yf.Ticker(simbolo or para_yahoo(ticker))
    hist = papel.history(period=periodo, auto_adjust=False)
    if hist is None or hist.empty:
        raise ValueError(f"sem histórico para {ticker}")
    dividendos = papel.dividends
    return hist["Close"], dividendos


def historico_yfinance(ticker: str, periodo: str = "1y", simbolo: str | None = None) -> dict[str, Any]:
    """
    Histórico de preços de fechamento e de dividendos pagos.

    Retorna listas prontas para gráfico:
        precos:     [{"data": "2026-01-02", "fechamento": 30.1}, ...]
        dividendos: [{"data": "2026-03-15", "valor": 0.85}, ...]
        dpa_12m:    soma dos dividendos dos últimos 365 dias
    """
    fechamentos, dividendos = _com_timeout(_historico, ticker, periodo, simbolo)

    precos = [
        {"data": idx.strftime("%Y-%m-%d"), "fechamento": round(float(v), 2)}
        for idx, v in fechamentos.dropna().items()
    ]
    # Remove fuso horário para comparar datas com segurança.
    if len(dividendos) and getattr(dividendos.index, "tz", None) is not None:
        dividendos.index = dividendos.index.tz_localize(None)
    limite_2a = pd.Timestamp.now() - pd.Timedelta(days=730)
    limite_1a = pd.Timestamp.now() - pd.Timedelta(days=365)
    div_recentes = dividendos[dividendos.index >= limite_2a] if len(dividendos) else dividendos
    lista_div = [
        {"data": idx.strftime("%Y-%m-%d"), "valor": round(float(v), 4)}
        for idx, v in div_recentes.items()
    ]
    dpa_12m = float(dividendos[dividendos.index >= limite_1a].sum()) if len(dividendos) else 0.0
    return {"precos": precos, "dividendos": lista_div, "dpa_12m": round(dpa_12m, 4)}


# ---------------------------------------------------------------------------
# brapi.dev (fonte secundária)
# ---------------------------------------------------------------------------

def cotacoes_brapi(tickers: list[str]) -> dict[str, dict[str, float]]:
    """
    Cotações via brapi.dev. Sem token, a API libera apenas alguns tickers de
    teste; com ``BRAPI_TOKEN`` no .env funciona para todos.
    """
    token = os.getenv("BRAPI_TOKEN", "").strip()
    params = {"token": token} if token else {}
    resultado: dict[str, dict[str, float]] = {}
    # Plano gratuito aceita 1 ticker por requisição.
    for ticker in tickers:
        try:
            resp = requests.get(URL_BRAPI.format(tickers=ticker), params=params, timeout=5)
            resp.raise_for_status()
            item = resp.json()["results"][0]
            resultado[ticker] = {
                "cotacao": round(float(item["regularMarketPrice"]), 2),
                "variacao_dia": round(float(item.get("regularMarketChangePercent") or 0), 2),
            }
        except Exception as erro:  # noqa: BLE001
            logger.debug("brapi falhou para %s: %s", ticker, erro)
    return resultado
