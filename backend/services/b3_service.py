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

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Any
from urllib.parse import urlencode

import pandas as pd
import requests

from services.http_seguro import baixar

logger = logging.getLogger("alpharadar.b3")

TIMEOUT_YFINANCE = 12  # segundos — evita que a API "trave" esperando o Yahoo
URL_BRAPI_V2 = "https://brapi.dev/api/v2/stocks/quote"

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
# brapi.dev — API v2, operação GET /api/v2/stocks/quote?symbols=PETR4,VALE3
# ---------------------------------------------------------------------------
# Docs: https://brapi.dev/llms.txt e https://brapi.dev/openapi.json. Resposta (por ticker):
#   {"requestedSymbol": "PETR4", "symbol": "PETR4", "changed": false,
#    "data": {"regularMarketPrice": 45.3, "regularMarketChangePercent": 1.34, ...}}
# Erros tratados: 400 QUOTES_PER_REQUEST_EXCEEDED (plano sem lotes), 401 (token inválido), 403 (plano não
# inclui o dado), 404 (nenhum ticker encontrado), 429 (cota/limite: respeita ``Retry-After``).

TICKERS_BRAPI_SEM_TOKEN = ("PETR4", "VALE3", "ITUB4", "MGLU3")  # únicos liberados sem token
LOTE_BRAPI = 10          # tickers por chamada (planos com lotes; o gratuito aceita 1)
PAUSA_MAXIMA_BRAPI = 300  # nunca fica mais de 5 min sem tentar a brapi, mesmo com Retry-After enorme

_plano_gratuito = False   # vira True quando a brapi recusa lotes (QUOTES_PER_REQUEST_EXCEEDED)
_pausa_ate = 0.0          # time.monotonic() até quando NÃO chamar a brapi (após 429, 401 ou 403)


def brapi_configurada() -> bool:
    return bool(os.getenv("BRAPI_TOKEN", "").strip())


def brapi_aceita_lotes() -> bool:
    """Com token e plano pago (lotes de até 10), a brapi pode ser a fonte principal da B3; no gratuito vira reserva."""
    return brapi_configurada() and not _plano_gratuito


def _pausar_brapi(segundos: float) -> None:
    global _pausa_ate
    _pausa_ate = time.monotonic() + min(max(segundos, 1.0), PAUSA_MAXIMA_BRAPI)


def _numero(valor: Any) -> float | None:
    """Campo da brapi pode vir null ou texto: devolve float ou None, nunca levanta exceção."""
    try:
        return None if valor is None else float(valor)
    except (TypeError, ValueError):
        return None


def _interpretar_v2(corpo: bytes) -> dict[str, dict[str, float]]:
    """results[] -> {ticker: {cotacao, variacao_dia}}. Ignora itens sem preço (campo null)."""
    saida: dict[str, dict[str, float]] = {}
    for item in json.loads(corpo).get("results") or []:
        dados = item.get("data") or {}
        preco = _numero(dados.get("regularMarketPrice"))
        simbolo = str(item.get("requestedSymbol") or item.get("symbol") or "").upper()
        if preco is None or not simbolo:
            continue
        variacao = _numero(dados.get("regularMarketChangePercent")) or 0.0
        saida[simbolo] = {"cotacao": round(preco, 2), "variacao_dia": round(variacao, 2)}
    return saida


def _lote_brapi(lote: list[str], cabecalhos: dict[str, str]) -> dict[str, dict[str, float]]:
    """Uma chamada v2 (até ``LOTE_BRAPI`` tickers em ``symbols``). Usa ``baixar``: teto de tamanho e só http(s)."""
    global _plano_gratuito
    url = f"{URL_BRAPI_V2}?{urlencode({'symbols': ','.join(lote)})}"
    try:
        return _interpretar_v2(baixar(url, timeout=8, headers=cabecalhos))
    except requests.HTTPError as erro:
        status = erro.response.status_code if erro.response is not None else 0
        corpo = getattr(erro, "corpo_erro", b"")
        if status == 400 and b"QUOTES_PER_REQUEST_EXCEEDED" in corpo:
            _plano_gratuito = True  # o plano não aceita lotes: nas próximas vezes busca 1 por chamada
        elif status == 404:
            pass  # nenhum dos tickers existe na brapi: não é falha, só não há cotação
        elif status == 429:
            espera = erro.response.headers.get("Retry-After", "")
            _pausar_brapi(float(espera) if espera.isdigit() else 60.0)
        elif status in (401, 403):
            _pausar_brapi(PAUSA_MAXIMA_BRAPI)  # token inválido ou plano sem acesso: repetir só gasta cota
        logger.warning("brapi recusou %d ticker(s): HTTP %s", len(lote), status)
        return {}


def cotacoes_brapi(tickers: list[str]) -> dict[str, dict[str, float]]:
    """
    Cotações via brapi.dev v2. O token (``BRAPI_TOKEN``) vai no cabeçalho ``Authorization: Bearer``, nunca na
    URL. Com plano de lotes busca 10 tickers por chamada, em paralelo; no gratuito, 1 por chamada; sem token,
    só os 4 tickers liberados. Após 429/401/403 fica em pausa (respeitando Retry-After) em vez de insistir.
    Campos null são ignorados; falha de um lote não derruba os outros.
    """
    if time.monotonic() < _pausa_ate:
        return {}
    token = os.getenv("BRAPI_TOKEN", "").strip()
    cabecalhos = {"User-Agent": "AlphaRadarB3/1.0"}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    if token and not _plano_gratuito:
        lotes = [tickers[i:i + LOTE_BRAPI] for i in range(0, len(tickers), LOTE_BRAPI)]
    elif token:
        lotes = [[t] for t in tickers]
    else:
        lotes = [[t] for t in tickers if t in TICKERS_BRAPI_SEM_TOKEN]
    resultado: dict[str, dict[str, float]] = {}

    def _um(lote: list[str]) -> dict[str, dict[str, float]]:
        if time.monotonic() < _pausa_ate:  # outro lote já levou 429
            return {}
        try:
            return _lote_brapi(lote, cabecalhos)
        except Exception as erro:  # noqa: BLE001
            logger.warning("brapi falhou (%d ticker(s)): %s", len(lote), type(erro).__name__)
            return {}

    with ThreadPoolExecutor(max_workers=4) as pool:
        for parcial in pool.map(_um, lotes):
            resultado.update(parcial)
    return {t: resultado[t] for t in tickers if t in resultado}
