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
from collections import OrderedDict
import zlib
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from services import b3_service, bcb_service, fundamentals_service

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
    """
    Cache em memória em que cada valor "expira" após ``ttl`` segundos.

    Defesas contra abuso (a API é pública):
      * Tamanho máximo (``max_itens``): ao passar do limite, descarta os itens menos recentes. Sem isso, quem
        mandasse milhares de perguntas diferentes à IA encheria a memória do servidor.
      * Uma busca por chave ("single-flight"): se 50 pedidos chegam ao mesmo tempo com o cache frio, só UM
        executa a consulta lenta (Yahoo, IA); os outros esperam e reaproveitam o resultado.
    """

    def __init__(self, max_itens: int = 2000) -> None:
        self._dados: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._trava = threading.Lock()
        self._travas_por_chave: dict[str, threading.Lock] = {}
        self._max_itens = max_itens

    def _fresco(self, chave: str, ttl: float) -> tuple[bool, Any]:
        with self._trava:
            item = self._dados.get(chave)
            if item and time.time() - item[0] < ttl:
                self._dados.move_to_end(chave)
                return True, item[1]
        return False, None

    def obter_ou_calcular(self, chave: str, ttl: float, calcular: Callable[[], Any]) -> Any:
        achou, valor = self._fresco(chave, ttl)
        if achou:
            return valor
        with self._trava:
            trava_da_chave = self._travas_por_chave.setdefault(chave, threading.Lock())
        with trava_da_chave:
            achou, valor = self._fresco(chave, ttl)  # outro pedido pode ter calculado enquanto esperávamos
            if achou:
                return valor
            try:
                valor = calcular()                   # fora da trava geral: pode ser lento
            finally:
                with self._trava:
                    self._travas_por_chave.pop(chave, None)
            with self._trava:
                self._dados[chave] = (time.time(), valor)
                self._dados.move_to_end(chave)
                while len(self._dados) > self._max_itens:
                    self._dados.popitem(last=False)
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


def simbolo_yahoo(ativo: dict[str, Any]) -> str:
    """Símbolo no Yahoo Finance: B3 usa sufixo ".SA" (PETR4.SA); EUA usa o próprio ticker (NVDA)."""
    return ativo.get("yahoo") or f"{ativo['ticker']}.SA"


def _completar_mercado(ativo: dict[str, Any]) -> None:
    """Ativos antigos do JSON não têm mercado/moeda: por padrão são da B3, em reais."""
    ativo.setdefault("mercado", "B3")
    ativo.setdefault("moeda", "BRL")


# ---------------------------------------------------------------------------
# Cotações e fundamentos
# ---------------------------------------------------------------------------

def _cotacoes_ao_vivo(ativos: list[dict[str, Any]]) -> tuple[dict[str, dict[str, float]], str]:
    """Tenta yfinance; completa o que faltar (só B3) com brapi.dev. Retorna (dados, fonte)."""
    if modo_offline():
        return {}, "fallback"
    tickers = [a["ticker"] for a in ativos]
    dados: dict[str, dict[str, float]] = {}
    try:
        dados = b3_service.cotacoes_yfinance(tickers, {a["ticker"]: simbolo_yahoo(a) for a in ativos})
    except Exception as erro:  # noqa: BLE001
        logger.warning("yfinance indisponível: %s", erro)
    faltando = [a["ticker"] for a in ativos if a["ticker"] not in dados and a["mercado"] == "B3"]
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
        for ativo in ativos:
            _completar_mercado(ativo)
        ao_vivo, fonte = _cotacoes_ao_vivo(ativos)
        dolar = float(indicadores_macro().get("dolar") or 0)
        for ativo in ativos:
            cot = ao_vivo.get(ativo["ticker"])
            ativo["fonte_cotacao"] = "ao_vivo" if cot else "fallback"
            if cot:
                ativo.update(cot)
            ativo.setdefault("fonte_fundamentos", "estimado")
            # Ações dos EUA: também em reais, pelo dólar do dia (só para referência).
            if ativo["moeda"] == "USD" and dolar:
                ativo["cotacao_brl"] = round(ativo["cotacao"] * dolar, 2)
        # Fundamentos reais (balanços) com cache de 6 h; falhou? seguem os valores de reserva do JSON.
        try:
            for ticker, campos in fundamentals_service.fundamentos_ao_vivo(ativos).items():
                alvo = next((a for a in ativos if a["ticker"] == ticker), None)
                if alvo:
                    fundamentals_service.aplicar_fundamentos(alvo, campos)
        except Exception as erro:  # noqa: BLE001
            logger.warning("Fundamentos ao vivo indisponíveis: %s", type(erro).__name__)
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
                dados = b3_service.historico_yfinance(ativo["ticker"], simbolo=simbolo_yahoo(ativo))
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
