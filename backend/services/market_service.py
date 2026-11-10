"""
market_service.py — Orquestrador de dados com resiliência (fallback)
======================================================================

Esta é a ÚNICA porta de entrada de dados de mercado para o resto do backend.
Ele combina:

    b3_service   (yfinance / brapi.dev) -> cotações, histórico, dividendos
    bcb_service  (API SGS do BCB)       -> Selic, CDI, IPCA
    data/fallback_b3.json               -> dados locais de segurança

Regra de ouro (exigência do projeto): NUNCA gerar erro 500 por falha externa.
Todo acesso à internet está dentro de ``try/except``; se falhar, devolvemos o
fallback e marcamos ``fonte = "fallback"`` para o frontend exibir um aviso.

Também há um CACHE em memória com tempo de expiração (TTL), para não
consultar o Yahoo/BCB a cada clique do usuário — isso deixa a API rápida e
evita bloqueio por excesso de requisições (rate limit).

Dica de estudo: defina ``ALPHARADAR_OFFLINE=1`` no .env para forçar o modo
offline e ver o fallback em ação.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import os
import random
import threading
import time
import zlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from services import b3_service, bcb_service

logger = logging.getLogger("alpharadar.market")

CAMINHO_FALLBACK = Path(__file__).resolve().parent.parent / "data" / "fallback_b3.json"
TTL_COTACOES = 5 * 60        # 5 minutos
TTL_MACRO = 30 * 60          # 30 minutos (Selic/IPCA mudam pouco)
TTL_HISTORICO = 60 * 60      # 1 hora


def modo_offline() -> bool:
    return os.getenv("ALPHARADAR_OFFLINE", "0").strip().lower() in {"1", "true", "sim", "yes"}


# ---------------------------------------------------------------------------
# Cache simples com TTL (thread-safe)
# ---------------------------------------------------------------------------

class CacheTTL:
    """Dicionário em que cada valor "expira" após ``ttl`` segundos."""

    def __init__(self) -> None:
        self._dados: dict[str, tuple[float, Any]] = {}
        self._trava = threading.Lock()

    def obter_ou_calcular(self, chave: str, ttl: float, calcular: Callable[[], Any]) -> Any:
        agora = time.time()
        with self._trava:
            item = self._dados.get(chave)
            if item and agora - item[0] < ttl:
                return item[1]
        valor = calcular()                       # fora da trava: pode ser lento
        with self._trava:
            self._dados[chave] = (time.time(), valor)
        return valor


_cache = CacheTTL()


# ---------------------------------------------------------------------------
# Fallback local
# ---------------------------------------------------------------------------

def carregar_fallback() -> dict[str, Any]:
    """Lê o JSON de segurança (cópia profunda para ninguém alterar o original)."""
    def _ler() -> dict[str, Any]:
        with CAMINHO_FALLBACK.open(encoding="utf-8") as arquivo:
            return json.load(arquivo)

    return copy.deepcopy(_cache.obter_ou_calcular("fallback", 10**9, _ler))


def tickers_monitorados() -> list[str]:
    return [a["ticker"] for a in carregar_fallback()["ativos"]]


# ---------------------------------------------------------------------------
# Cotações e fundamentos
# ---------------------------------------------------------------------------

def _cotacoes_ao_vivo(tickers: list[str]) -> tuple[dict[str, dict[str, float]], str]:
    """Tenta yfinance; completa o que faltar com brapi.dev. Retorna (dados, fonte)."""
    if modo_offline():
        return {}, "fallback"
    dados: dict[str, dict[str, float]] = {}
    try:
        dados = b3_service.cotacoes_yfinance(tickers)
    except Exception as erro:  # noqa: BLE001
        logger.warning("yfinance indisponível: %s", erro)
    faltando = [t for t in tickers if t not in dados]
    if faltando:
        try:
            dados.update(b3_service.cotacoes_brapi(faltando))
        except Exception as erro:  # noqa: BLE001
            logger.warning("brapi indisponível: %s", erro)
    if not dados:
        return {}, "fallback"
    return dados, ("ao_vivo" if len(dados) == len(tickers) else "misto")


def listar_ativos() -> dict[str, Any]:
    """
    Devolve os 16 ativos monitorados com fundamentos (do JSON) e cotação
    atualizada (yfinance/brapi quando disponível).

    Observação didática: fundamentos como LPA, VPA e ROE mudam a cada
    balanço trimestral, então mantê-los num arquivo versionado é aceitável;
    o que muda a cada minuto é a cotação — e essa vem ao vivo.
    """
    def _calcular() -> dict[str, Any]:
        base = carregar_fallback()
        ativos = base["ativos"]
        ao_vivo, fonte = _cotacoes_ao_vivo([a["ticker"] for a in ativos])
        for ativo in ativos:
            cot = ao_vivo.get(ativo["ticker"])
            ativo["fonte_cotacao"] = "ao_vivo" if cot else "fallback"
            if cot:
                ativo.update(cot)
        return {"ativos": ativos, "fonte": fonte, "atualizado_em": time.strftime("%Y-%m-%d %H:%M:%S")}

    return copy.deepcopy(_cache.obter_ou_calcular("ativos", TTL_COTACOES, _calcular))


def obter_ativo(ticker: str) -> dict[str, Any] | None:
    ticker = ticker.upper().replace(".SA", "")
    for ativo in listar_ativos()["ativos"]:
        if ativo["ticker"] == ticker:
            return ativo
    return None


# ---------------------------------------------------------------------------
# Indicadores macro
# ---------------------------------------------------------------------------

def indicadores_macro() -> dict[str, Any]:
    """Selic/CDI/IPCA (BCB) + Ibovespa/Dólar/S&P/Brent (yfinance), com fallback."""
    def _calcular() -> dict[str, Any]:
        macro = carregar_fallback()["macro"]
        fontes = {"bcb": "fallback", "mercado": "fallback"}
        if not modo_offline():
            try:
                bcb = bcb_service.buscar_indicadores_macro()
                if bcb:
                    macro.update(bcb)
                    fontes["bcb"] = "ao_vivo"
            except Exception as erro:  # noqa: BLE001
                logger.warning("BCB indisponível: %s", erro)
            try:
                mercado = b3_service.macro_yfinance()
                if mercado:
                    macro.update(mercado)
                    fontes["mercado"] = "ao_vivo"
            except Exception as erro:  # noqa: BLE001
                logger.warning("Índices indisponíveis: %s", erro)
        # Juro real aproximado (fórmula de Fisher): (1+i)/(1+π) − 1
        macro["juro_real"] = round(((1 + macro["selic_anual"] / 100) / (1 + macro["ipca_12m"] / 100) - 1) * 100, 2)
        macro["fontes"] = fontes
        return macro

    return copy.deepcopy(_cache.obter_ou_calcular("macro", TTL_MACRO, _calcular))


# ---------------------------------------------------------------------------
# Histórico de preços e dividendos
# ---------------------------------------------------------------------------

def _historico_sintetico(ativo: dict[str, Any], dias_uteis: int = 252) -> dict[str, Any]:
    """
    Gera um histórico ILUSTRATIVO e determinístico (mesma semente = mesmo
    gráfico) quando não há internet. É um "passeio aleatório" (random walk)
    que termina exatamente na cotação atual.
    """
    semente = zlib.crc32(ativo["ticker"].encode())
    rng = random.Random(semente)
    vol_diaria = 0.012 * (ativo.get("beta") or 1.0)
    preco = float(ativo["cotacao"])
    serie: list[float] = [preco]
    for _ in range(dias_uteis - 1):                # andamos para TRÁS no tempo
        preco = preco / math.exp(rng.gauss(0.0002, vol_diaria))
        serie.append(preco)
    serie.reverse()

    hoje = date.today()
    datas: list[date] = []
    d = hoje
    while len(datas) < dias_uteis:
        if d.weekday() < 5:                        # ignora sábados e domingos
            datas.append(d)
        d -= timedelta(days=1)
    datas.reverse()
    precos = [{"data": dt.isoformat(), "fechamento": round(p, 2)} for dt, p in zip(datas, serie)]

    # FIIs pagam todo mês; ações, em geral, a cada trimestre.
    parcelas = 12 if ativo.get("tipo") == "fii" else 4
    intervalo = 12 // parcelas
    valor = float(ativo.get("dpa_12m") or 0) / parcelas
    dividendos = []
    if valor > 0:
        for i in range(parcelas * 2):              # 2 anos de proventos
            mes = hoje.replace(day=15) - timedelta(days=30 * intervalo * i)
            dividendos.append({"data": mes.isoformat(), "valor": round(valor * (0.97 if i >= parcelas else 1), 4)})
        dividendos.reverse()
    return {"precos": precos, "dividendos": dividendos, "dpa_12m": ativo.get("dpa_12m") or 0}


def historico_ativo(ticker: str) -> dict[str, Any]:
    """Histórico de 1 ano + dividendos de 2 anos, com fallback sintético."""
    ativo = obter_ativo(ticker)
    if ativo is None:
        return {"precos": [], "dividendos": [], "dpa_12m": 0, "fonte": "indisponivel"}

    def _calcular() -> dict[str, Any]:
        if not modo_offline():
            try:
                dados = b3_service.historico_yfinance(ativo["ticker"])
                if dados["precos"]:
                    dados["fonte"] = "ao_vivo"
                    return dados
            except Exception as erro:  # noqa: BLE001
                logger.warning("Histórico de %s indisponível: %s", ticker, erro)
        dados = _historico_sintetico(ativo)
        dados["fonte"] = "fallback"
        return dados

    return copy.deepcopy(_cache.obter_ou_calcular(f"hist:{ativo['ticker']}", TTL_HISTORICO, _calcular))


def estatisticas_risco(precos: list[dict[str, Any]]) -> dict[str, float | None]:
    """
    Métricas de risco a partir do histórico (usando pandas):
        - volatilidade anualizada = desvio-padrão dos retornos diários × √252
        - máximo drawdown = maior queda do topo ao fundo no período
        - retorno no período
    """
    import pandas as pd

    if len(precos) < 20:
        return {"volatilidade_anual": None, "max_drawdown": None, "retorno_periodo": None}
    serie = pd.Series([p["fechamento"] for p in precos], dtype="float64")
    retornos = serie.pct_change().dropna()
    volatilidade = float(retornos.std() * math.sqrt(252) * 100)
    pico = serie.cummax()
    drawdown = float(((serie / pico) - 1).min() * 100)
    retorno = float((serie.iloc[-1] / serie.iloc[0] - 1) * 100)
    return {
        "volatilidade_anual": round(volatilidade, 2),
        "max_drawdown": round(drawdown, 2),
        "retorno_periodo": round(retorno, 2),
    }
