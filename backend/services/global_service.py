"""
global_service.py — Panorama global: bolsas, moedas, cripto, commodities, juros, Focus e agenda
===============================================================================================

Reúne em um só lugar o que o investidor precisa olhar antes de decidir:

    1. Bolsas do mundo, moedas, criptomoedas, commodities e juros dos EUA (Yahoo Finance)
    2. Termômetro de apetite a risco (regras simples sobre VIX, S&P 500, dólar global e Ibovespa)
    3. Série "juros dos EUA × Ibovespa" dos últimos 6 meses (a relação inversa clássica)
    4. Expectativas do mercado para Selic, IPCA, PIB e câmbio (Boletim Focus do Banco Central)
    5. Agenda econômica da semana (feed público: EUA, Europa, Reino Unido, Japão, China...)

Todas as seções têm fallback: se uma fonte falhar, o restante continua funcionando.
O Brasil não tem feed gratuito e estruturado de agenda; as expectativas do Focus cobrem a visão local.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests

from services import b3_service, market_service

logger = logging.getLogger("alpharadar.global")

CAMINHO_FALLBACK = Path(__file__).resolve().parent.parent / "data" / "fallback_mercado.json"
TTL_MERCADO = 5 * 60
TTL_FOCUS = 6 * 3600
TTL_AGENDA = 30 * 60

# (grupo, nome, símbolo no Yahoo, unidade, tipo de variação: "pct" ou "pp" para juros)
ATIVOS_GLOBAIS: list[tuple[str, str, str, str, str]] = [
    ("bolsas", "Ibovespa", "^BVSP", "pts", "pct"),
    ("bolsas", "S&P 500", "^GSPC", "pts", "pct"),
    ("bolsas", "Nasdaq", "^IXIC", "pts", "pct"),
    ("bolsas", "Dow Jones", "^DJI", "pts", "pct"),
    ("bolsas", "Euro Stoxx 50", "^STOXX50E", "pts", "pct"),
    ("bolsas", "DAX (Alemanha)", "^GDAXI", "pts", "pct"),
    ("bolsas", "FTSE 100 (Reino Unido)", "^FTSE", "pts", "pct"),
    ("bolsas", "Nikkei (Japão)", "^N225", "pts", "pct"),
    ("bolsas", "Hang Seng (Hong Kong)", "^HSI", "pts", "pct"),
    ("bolsas", "Xangai (China)", "000001.SS", "pts", "pct"),
    ("moedas", "Dólar", "USDBRL=X", "R$", "pct"),
    ("moedas", "Euro", "EURBRL=X", "R$", "pct"),
    ("moedas", "Libra", "GBPBRL=X", "R$", "pct"),
    ("moedas", "Índice do dólar (DXY)", "DX-Y.NYB", "pts", "pct"),
    ("cripto", "Bitcoin", "BTC-USD", "US$", "pct"),
    ("cripto", "Ethereum", "ETH-USD", "US$", "pct"),
    ("commodities", "Petróleo WTI", "CL=F", "US$", "pct"),
    ("commodities", "Petróleo Brent", "BZ=F", "US$", "pct"),
    ("commodities", "Ouro", "GC=F", "US$", "pct"),
    ("commodities", "Prata", "SI=F", "US$", "pct"),
    ("commodities", "Cobre", "HG=F", "US$", "pct"),
    ("commodities", "Minério de ferro", "TIO=F", "US$", "pct"),
    ("juros_eua", "Treasury 13 semanas", "^IRX", "%", "pp"),
    ("juros_eua", "Treasury 5 anos", "^FVX", "%", "pp"),
    ("juros_eua", "Treasury 10 anos", "^TNX", "%", "pp"),
    ("juros_eua", "Treasury 30 anos", "^TYX", "%", "pp"),
    ("volatilidade", "VIX (índice do medo)", "^VIX", "pts", "pct"),
]

ROTULOS_GRUPOS = {
    "bolsas": "Bolsas do mundo",
    "moedas": "Moedas contra o real",
    "cripto": "Criptomoedas",
    "commodities": "Commodities",
    "juros_eua": "Juros dos EUA",
    "volatilidade": "Volatilidade",
}


def _carregar_fallback() -> dict[str, Any]:
    with CAMINHO_FALLBACK.open(encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 1. Cotações globais
# ---------------------------------------------------------------------------

def _montar_grupos(cotacoes: dict[str, dict[str, float]]) -> dict[str, list[dict[str, Any]]]:
    grupos: dict[str, list[dict[str, Any]]] = {g: [] for g in ROTULOS_GRUPOS}
    for grupo, nome, simbolo, unidade, tipo in ATIVOS_GLOBAIS:
        c = cotacoes.get(simbolo)
        if not c:
            continue
        valor, var_pct = c["cotacao"], c["variacao_dia"]
        item = {"nome": nome, "simbolo": simbolo, "unidade": unidade, "valor": valor, "variacao": var_pct, "tipo_variacao": tipo}
        if tipo == "pp":  # juros: o que importa é a variação em pontos percentuais, não em %
            anterior = valor / (1 + var_pct / 100) if var_pct > -100 else valor
            item["variacao"] = round(valor - anterior, 3)
        grupos[grupo].append(item)
    return grupos


def _valor(grupos: dict[str, list[dict[str, Any]]], simbolo: str) -> dict[str, Any] | None:
    for itens in grupos.values():
        for i in itens:
            if i["simbolo"] == simbolo:
                return i
    return None


def termometro_risco(grupos: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """
    Apetite a risco (risk-on / risk-off) por regras simples e explicáveis.

    Cada sinal soma ou subtrai pontos; o total vira um rótulo. É uma leitura do DIA,
    não uma previsão: serve para contextualizar quedas e altas.
    """
    pontos, motivos = 0, []
    vix, spx, dxy, ibov = (_valor(grupos, s) for s in ("^VIX", "^GSPC", "DX-Y.NYB", "^BVSP"))
    if vix:
        if vix["valor"] >= 25:
            pontos -= 2; motivos.append(f"VIX alto ({vix['valor']:.1f}): o mercado precifica muita instabilidade.")
        elif vix["valor"] >= 20:
            pontos -= 1; motivos.append(f"VIX elevado ({vix['valor']:.1f}): cautela nos EUA.")
        elif vix["valor"] <= 16:
            pontos += 1; motivos.append(f"VIX baixo ({vix['valor']:.1f}): ambiente calmo.")
    if spx:
        if spx["variacao"] >= 0.5:
            pontos += 1; motivos.append(f"S&P 500 em alta ({spx['variacao']:+.2f}%).")
        elif spx["variacao"] <= -0.5:
            pontos -= 1; motivos.append(f"S&P 500 em queda ({spx['variacao']:+.2f}%).")
    if dxy:
        if dxy["variacao"] >= 0.5:
            pontos -= 1; motivos.append("Dólar global forte: tende a pressionar emergentes como o Brasil.")
        elif dxy["variacao"] <= -0.5:
            pontos += 1; motivos.append("Dólar global fraco: favorece emergentes como o Brasil.")
    if ibov:
        if ibov["variacao"] >= 1:
            pontos += 1; motivos.append(f"Ibovespa em alta ({ibov['variacao']:+.2f}%).")
        elif ibov["variacao"] <= -1:
            pontos -= 1; motivos.append(f"Ibovespa em queda ({ibov['variacao']:+.2f}%).")
    rotulo = "Apetite alto" if pontos >= 2 else "Apetite baixo" if pontos <= -2 else "Neutro"
    return {"pontos": pontos, "rotulo": rotulo, "motivos": motivos or ["Sem sinais fortes hoje."]}


def _serie_juros_bolsa() -> list[dict[str, Any]]:
    """Ibovespa (base 100) e juro de 10 anos dos EUA nos últimos 6 meses: a relação clássica juros × bolsa."""
    import pandas as pd
    import yfinance as yf

    dados = yf.download("^BVSP ^TNX", period="6mo", interval="1d", progress=False, auto_adjust=False, group_by="column")["Close"]
    dados = dados.dropna()
    if dados.empty:
        raise ValueError("série vazia")
    base = float(dados["^BVSP"].iloc[0])
    return [
        {"data": idx.strftime("%Y-%m-%d") if isinstance(idx, pd.Timestamp) else str(idx),
         "ibovespa": round(float(r["^BVSP"]) / base * 100, 2), "juro_10a_eua": round(float(r["^TNX"]), 3)}
        for idx, r in dados.iterrows()
    ]


def panorama_global() -> dict[str, Any]:
    def _calcular() -> dict[str, Any]:
        fb = _carregar_fallback()
        fonte, grupos, serie = "fallback", fb["grupos"], fb.get("serie_juros_bolsa", [])
        if not market_service.modo_offline():
            try:
                simbolos = [a[2] for a in ATIVOS_GLOBAIS]
                cot = b3_service.cotacoes_yfinance(simbolos, {s: s for s in simbolos})
                if cot:
                    ao_vivo = _montar_grupos(cot)
                    # o que não veio ao vivo completa com o fallback (marcado como "misto")
                    for g, itens in fb["grupos"].items():
                        faltam = [i for i in itens if i["simbolo"] not in {x["simbolo"] for x in ao_vivo[g]}]
                        ao_vivo[g].extend(faltam)
                    grupos, fonte = ao_vivo, ("ao_vivo" if len(cot) >= len(simbolos) - 1 else "misto")
            except Exception as erro:  # noqa: BLE001
                logger.warning("Mercado global indisponível: %s", type(erro).__name__)
            try:
                serie = b3_service._com_timeout(_serie_juros_bolsa, timeout=20) or serie
            except Exception as erro:  # noqa: BLE001
                logger.warning("Série juros x bolsa indisponível: %s", type(erro).__name__)
        return {
            "grupos": [{"id": g, "titulo": ROTULOS_GRUPOS[g], "itens": itens} for g, itens in grupos.items() if itens],
            "risco": termometro_risco(grupos),
            "serie_juros_bolsa": serie,
            "fonte": fonte,
            "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    return copy.deepcopy(market_service._cache.obter_ou_calcular("global", TTL_MERCADO, _calcular))


# ---------------------------------------------------------------------------
# 2. Boletim Focus (Banco Central)
# ---------------------------------------------------------------------------

URL_FOCUS = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
INDICADORES_FOCUS = [("Selic", "Selic (fim do ano)", "% a.a."), ("IPCA", "IPCA (inflação)", "% no ano"),
                     ("PIB Total", "PIB (crescimento)", "% no ano"), ("Câmbio", "Dólar (fim do ano)", "R$")]


def _buscar_focus() -> dict[str, Any]:
    saida = []
    data_boletim = ""
    for indicador, rotulo, unidade in INDICADORES_FOCUS:
        # A API OData do BCB não aceita "+" como espaço: a URL é montada à mão (requests converte espaço em %20).
        consulta = f"$top=40&$filter=Indicador eq '{indicador}' and baseCalculo eq 0&$orderby=Data desc&$format=json"
        resp = requests.get(f"{URL_FOCUS}?{consulta}", timeout=15)
        resp.raise_for_status()
        linhas = resp.json()["value"]
        if not linhas:
            continue
        ultima = linhas[0]["Data"]
        data_boletim = max(data_boletim, ultima)
        anos = sorted((l for l in linhas if l["Data"] == ultima), key=lambda l: l["DataReferencia"])[:4]
        saida.append({
            "indicador": rotulo, "unidade": unidade,
            "anos": [{"ano": a["DataReferencia"], "mediana": a["Mediana"], "minimo": a["Minimo"], "maximo": a["Maximo"]} for a in anos],
        })
    if not saida:
        raise ValueError("Focus sem dados")
    return {"data_boletim": data_boletim, "indicadores": saida}


def expectativas_focus() -> dict[str, Any]:
    def _calcular() -> dict[str, Any]:
        if not market_service.modo_offline():
            try:
                return {**_buscar_focus(), "fonte": "ao_vivo"}
            except Exception as erro:  # noqa: BLE001
                logger.warning("Focus indisponível: %s", type(erro).__name__)
        return {**_carregar_fallback()["focus"], "fonte": "fallback"}

    return copy.deepcopy(market_service._cache.obter_ou_calcular("focus", TTL_FOCUS, _calcular))


# ---------------------------------------------------------------------------
# 3. Agenda econômica da semana
# ---------------------------------------------------------------------------

URLS_AGENDA = ["https://nfs.faireconomy.media/ff_calendar_thisweek.json", "https://nfs.faireconomy.media/ff_calendar_nextweek.json"]
PAISES = {"USD": "Estados Unidos", "EUR": "Zona do Euro", "GBP": "Reino Unido", "JPY": "Japão", "CNY": "China",
          "AUD": "Austrália", "CAD": "Canadá", "CHF": "Suíça", "NZD": "Nova Zelândia"}
# Tradução dos eventos mais comuns (o feed vem em inglês). Ordem importa: o mais específico primeiro.
TRADUCOES: list[tuple[str, str]] = [
    (r"Non-Farm Employment Change|Non-Farm Payrolls", "Criação de empregos (payroll)"),
    (r"Core CPI", "Inflação núcleo ao consumidor (CPI)"),
    (r"Core PCE", "Inflação núcleo PCE"),
    (r"\bCPI\b", "Inflação ao consumidor (CPI)"),
    (r"\bPPI\b", "Inflação ao produtor (PPI)"),
    (r"FOMC Meeting Minutes", "Ata do Fed (FOMC)"),
    (r"FOMC|Federal Funds Rate", "Decisão de juros do Fed"),
    (r"Main Refinancing Rate|ECB.*Rate|Monetary Policy Statement", "Decisão de juros do BCE"),
    (r"Official Bank Rate|MPC", "Decisão de juros do Banco da Inglaterra"),
    (r"BOJ Policy Rate|BOJ", "Decisão de juros do Banco do Japão"),
    (r"Unemployment Rate", "Taxa de desemprego"),
    (r"Unemployment Claims", "Pedidos de seguro-desemprego"),
    (r"\bGDP\b", "PIB"),
    (r"Retail Sales", "Vendas no varejo"),
    (r"Manufacturing PMI", "PMI industrial"),
    (r"Services PMI", "PMI de serviços"),
    (r"ISM", "Índice ISM"),
    (r"Speaks|Speech|Testifies", "Discurso de autoridade monetária"),
    (r"Trade Balance", "Balança comercial"),
    (r"Consumer Confidence|Consumer Sentiment", "Confiança do consumidor"),
    (r"Crude Oil Inventories", "Estoques de petróleo dos EUA"),
]
IMPACTOS = {"High": "alto", "Medium": "medio", "Low": "baixo"}


def _traduzir(titulo: str) -> str:
    for padrao, texto in TRADUCOES:
        if re.search(padrao, titulo, flags=re.I):
            return f"{texto} ({titulo})" if len(titulo) < 45 else texto
    return titulo


def _buscar_agenda() -> list[dict[str, Any]]:
    fuso = ZoneInfo("America/Sao_Paulo")
    eventos: list[dict[str, Any]] = []
    for url in URLS_AGENDA:
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0 AlphaRadarB3"})
            resp.raise_for_status()
            bruto = resp.json()
        except Exception as erro:  # noqa: BLE001
            logger.warning("Agenda %s indisponível: %s", url.rsplit("/", 1)[-1], type(erro).__name__)
            continue
        for e in bruto:
            impacto = IMPACTOS.get(e.get("impact", ""))
            if impacto is None or impacto == "baixo" or e.get("country") not in PAISES:
                continue
            try:
                quando = datetime.fromisoformat(e["date"]).astimezone(fuso)
            except (KeyError, ValueError):
                continue
            eventos.append({
                "quando": quando.strftime("%Y-%m-%dT%H:%M"), "pais": PAISES[e["country"]], "evento": _traduzir(e.get("title", "")),
                "impacto": impacto, "previsto": e.get("forecast") or "", "anterior": e.get("previous") or "",
            })
    limite = datetime.now() - timedelta(hours=6)
    eventos = [e for e in eventos if datetime.fromisoformat(e["quando"]) >= limite]
    eventos.sort(key=lambda e: e["quando"])
    return eventos


def agenda_economica() -> dict[str, Any]:
    def _calcular() -> dict[str, Any]:
        eventos: list[dict[str, Any]] = []
        if not market_service.modo_offline():
            try:
                eventos = _buscar_agenda()
            except Exception as erro:  # noqa: BLE001
                logger.warning("Agenda indisponível: %s", type(erro).__name__)
        return {"eventos": eventos[:40], "fonte": "ao_vivo" if eventos else "indisponivel"}

    return copy.deepcopy(market_service._cache.obter_ou_calcular("agenda", TTL_AGENDA, _calcular))
