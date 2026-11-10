"""
news_service.py — Radar de Notícias e Cadeia de Impacto
=========================================================

Responsabilidades:
    1. Classificar o SENTIMENTO de uma notícia (Positivo, Neutro, Negativo)
       com um léxico de palavras em português (técnica clássica de NLP,
       sem precisar de IA paga).
    2. Mapear a CADEIA DE IMPACTO: dado um evento (ex.: "Selic sobe"),
       quais ações, FIIs e produtos de renda fixa ganham ou perdem.
       Isso é feito por uma MATRIZ SETORIAL escrita à mão (regras de negócio).
    3. Calcular o sentimento médio por ativo (alimenta o 5º pilar do Score Alpha).

Fontes:
    - Por padrão, as 12 notícias de demonstração de ``data/fallback_b3.json``.
    - Opcional: defina ``NEWS_RSS_URLS`` no .env (URLs separadas por vírgula)
      para ler manchetes reais de feeds RSS; elas passam pelo mesmo
      classificador e pela mesma matriz de impacto.
"""

from __future__ import annotations

import copy
import hashlib
import logging
import math
import os
import re
import unicodedata
import defusedxml.ElementTree as ET  # parser XML seguro contra XXE e "billion laughs"
from email.utils import parsedate_to_datetime
from typing import Any

import requests

from services import market_service, news_apis

logger = logging.getLogger("alpharadar.news")

PESO_IMPACTO: dict[str, float] = {"alto": 1.0, "medio": 0.6, "baixo": 0.3}


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos: 'Inflação' -> 'inflacao' (facilita comparar)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.lower()


# ---------------------------------------------------------------------------
# 1. Classificador de sentimento por léxico
# ---------------------------------------------------------------------------

PALAVRAS_POSITIVAS = {
    "sobe", "alta", "avanca", "cresce", "crescimento", "recorde", "lucro", "supera",
    "melhora", "recupera", "desacelera", "alivio", "valoriza", "otimismo", "aprova",
    "expansao", "forte", "ganho", "dividendos", "minima", "reduz", "queda da inflacao",
}
PALAVRAS_NEGATIVAS = {
    "cai", "queda", "recua", "despenca", "prejuizo", "crise", "incerteza", "risco",
    "piora", "rebaixa", "inadimplencia", "pressiona", "deficit", "perda", "fraco",
    "estoques elevados", "competicao", "tensao", "sobem com incerteza",
}


def classificar_sentimento(texto: str) -> tuple[float, str]:
    """
    Conta palavras positivas e negativas e devolve (índice de -1 a +1, rótulo).

    Índice = (positivas − negativas) ÷ (positivas + negativas)
    É simples de propósito: totalmente explicável numa entrevista.
    """
    t = normalizar(texto)
    pos = sum(1 for p in PALAVRAS_POSITIVAS if p in t)
    neg = sum(1 for p in PALAVRAS_NEGATIVAS if p in t)
    if pos + neg == 0:
        return 0.0, "Neutro"
    indice = (pos - neg) / (pos + neg)
    return indice, rotulo_sentimento(indice)


def rotulo_sentimento(indice: float) -> str:
    if indice > 0.15:
        return "Positivo"
    if indice < -0.15:
        return "Negativo"
    return "Neutro"


# ---------------------------------------------------------------------------
# 2. Matriz setorial de impacto (regras de negócio autorais)
# ---------------------------------------------------------------------------
# Cada tema tem: gatilhos (palavras-chave), quem se beneficia, quem é
# prejudicado e o efeito na renda fixa. A lógica econômica está no comentário.

MATRIZ_IMPACTO: dict[str, dict[str, Any]] = {
    "selic_alta": {
        # Juros altos: bancos e seguradoras ganham com o "float"; FIIs de papel
        # (CRIs indexados ao CDI) rendem mais; varejo e empresas endividadas sofrem.
        "gatilhos": ["selic sobe", "alta da selic", "eleva selic", "eleva a selic", "juros altos", "juros futuros sobem", "aperto monetario"],
        "beneficiados": ["BBAS3", "ITUB4", "BBSE3", "MXRF11"],
        "prejudicados": ["RENT3", "RADL3", "HGLG11", "XPML11", "KNRI11"],
        "renda_fixa": "Pós-fixados (CDB, LCI, LCA, Tesouro Selic) passam a render mais.",
    },
    "selic_queda": {
        # Juros menores: crédito mais barato, consumo e imóveis se valorizam.
        "gatilhos": ["corte da selic", "corta selic", "reduz a selic", "queda dos juros", "juros menores", "afrouxamento"],
        "beneficiados": ["RENT3", "RADL3", "HGLG11", "XPML11", "KNRI11", "WEGE3"],
        "prejudicados": ["MXRF11"],
        "renda_fixa": "Prefixados longos se valorizam; pós-fixados passam a render menos.",
    },
    "inflacao_queda": {
        "gatilhos": ["inflacao desacelera", "ipca desacelera", "ipca abaixo", "deflacao", "alivio na inflacao"],
        "beneficiados": ["RENT3", "RADL3", "HGLG11", "KNRI11", "XPML11"],
        "prejudicados": ["MXRF11"],
        "renda_fixa": "Abre espaço para cortes de juros: bom momento para travar prefixados.",
    },
    "inflacao_alta": {
        "gatilhos": ["inflacao acelera", "ipca acima", "ipca sobe", "pressao inflacionaria"],
        "beneficiados": ["MXRF11", "TAEE11", "EGIE3"],   # receitas/contratos corrigidos por inflação
        "prejudicados": ["RADL3", "RENT3"],
        "renda_fixa": "Tesouro IPCA+ protege o poder de compra.",
    },
    "petroleo_alta": {
        "gatilhos": ["petroleo sobe", "brent sobe", "alta do petroleo", "petroleo dispara"],
        "beneficiados": ["PETR4", "PRIO3"],
        "prejudicados": ["RENT3"],
        "renda_fixa": "Combustível mais caro pressiona a inflação e adia cortes de juros.",
    },
    "petroleo_queda": {
        "gatilhos": ["petroleo recua", "petroleo cai", "brent recua", "brent cai", "queda do petroleo"],
        "beneficiados": ["RENT3"],
        "prejudicados": ["PETR4", "PRIO3"],
        "renda_fixa": "Alivia a inflação e pode antecipar cortes da Selic.",
    },
    "dolar_alta": {
        # Exportadoras recebem em dólar e gastam em real.
        "gatilhos": ["dolar sobe", "alta do dolar", "real se desvaloriza", "dolar dispara"],
        "beneficiados": ["SUZB3", "VALE3", "WEGE3", "PRIO3"],
        "prejudicados": ["RENT3", "RADL3"],
        "renda_fixa": "Dólar alto pressiona a inflação de importados.",
    },
    "dolar_queda": {
        "gatilhos": ["dolar recua", "dolar cai", "real se valoriza", "fluxo estrangeiro"],
        "beneficiados": ["RENT3", "RADL3", "ITUB4", "BBAS3"],
        "prejudicados": ["SUZB3", "VALE3", "WEGE3"],
        "renda_fixa": "Real forte ajuda a conter a inflação.",
    },
    "minerio_alta": {
        "gatilhos": ["minerio sobe", "minerio de ferro sobe", "estimulos na china", "estimulos a construcao"],
        "beneficiados": ["VALE3"],
        "prejudicados": [],
        "renda_fixa": "Efeito neutro.",
    },
    "safra_agro": {
        "gatilhos": ["safra", "agronegocio", "agro"],
        "beneficiados": ["BBAS3"],      # maior financiador do agro no Brasil
        "prejudicados": [],
        "renda_fixa": "Mais emissões de LCA (isentas de IR) no mercado.",
    },
    "fiscal_risco": {
        "gatilhos": ["incerteza fiscal", "meta fiscal", "risco fiscal", "deficit"],
        "beneficiados": ["MXRF11", "BBSE3"],
        "prejudicados": ["RENT3", "WEGE3", "HGLG11", "XPML11", "EGIE3", "TAEE11"],
        "renda_fixa": "Tesouro IPCA+ e prefixados passam a pagar taxas maiores.",
    },
    "imobiliario_forte": {
        "gatilhos": ["vacancia", "galpoes", "logistica", "shoppings", "aluguel"],
        "beneficiados": ["HGLG11", "KNRI11", "XPML11"],
        "prejudicados": [],
        "renda_fixa": "FIIs de tijolo ganham prêmio sobre LCIs.",
    },
}


def mapear_impacto(texto: str) -> dict[str, Any]:
    """Aplica a matriz setorial a um texto livre (manchete + resumo)."""
    t = normalizar(texto)
    temas, benef, prej, rf = [], set(), set(), []
    for tema, regra in MATRIZ_IMPACTO.items():
        if any(g in t for g in regra["gatilhos"]):
            temas.append(tema)
            benef.update(regra["beneficiados"])
            prej.update(regra["prejudicados"])
            rf.append(regra["renda_fixa"])
    # Um ativo não pode estar nas duas listas: o conflito vira "neutro".
    conflito = benef & prej
    return {
        "temas": temas,
        "beneficiados": sorted(benef - conflito),
        "prejudicados": sorted(prej - conflito),
        "renda_fixa": " ".join(rf) or "Sem efeito relevante identificado.",
    }


def grau_impacto(texto: str, n_ativos: int) -> str:
    """Heurística: quantos ativos afetados + palavras de forte repercussão."""
    t = normalizar(texto)
    if n_ativos >= 5 or any(p in t for p in ("copom", "selic", "fiscal", "ipca")):
        return "alto"
    return "medio" if n_ativos >= 2 else "baixo"


# ---------------------------------------------------------------------------
# 3. Coleta de notícias (demonstração + RSS opcional)
# ---------------------------------------------------------------------------

PALAVRAS_MERCADO = (
    "bolsa", "ibovespa", "b3", "selic", "copom", "juros", "dolar", "cambio", "inflacao", "ipca", "pib",
    "dividendo", "fii", "fundo imobiliario", "fundos imobiliarios", "acoes", "acao ", "petroleo", "brent",
    "minerio", "banco", "lucro", "balanco", "tesouro", "cdb", "lci", "lca", "fiscal", "investidor",
    "petrobras", "vale", "itau", "bradesco", "weg", "suzano", "localiza", "raia", "taesa", "engie", "prio",
)


def _eh_de_mercado(texto: str, tem_tema: bool) -> bool:
    """Descarta política, saúde, esporte etc. dos feeds gerais: só entra o que fala de mercado."""
    t = normalizar(texto)
    return tem_tema or any(p in t for p in PALAVRAS_MERCADO)


def _montar_item(titulo: str, resumo: str, data_iso: str, link: str | None, origem: str,
                 idioma: str = "pt", filtrar: bool = True) -> dict[str, Any] | None:
    """
    Transforma uma manchete crua no formato do radar (sentimento, impacto, ativos afetados).

    Textos em inglês (Guardian, NYT) entram como contexto global: o classificador e a
    matriz de impacto são em português, então ficam neutros e sem ativos ligados.
    """
    texto = f"{titulo}. {resumo}"
    if idioma == "pt":
        sent, _ = classificar_sentimento(texto)
        impacto = mapear_impacto(texto)
        if filtrar and not _eh_de_mercado(texto, bool(impacto["temas"])):
            return None
    else:
        sent = 0.0
        impacto = {"temas": [], "beneficiados": [], "prejudicados": [], "renda_fixa": "Notícia global: contexto para câmbio e juros."}
    n_afetados = len(impacto["beneficiados"]) + len(impacto["prejudicados"])
    return {
        "id": "n-" + hashlib.md5(titulo.encode()).hexdigest()[:10],
        "titulo": titulo,
        "resumo": resumo,
        "categoria": "Mercado" if idioma == "pt" else "Mundo",
        "data": data_iso,
        "link": link,
        "sentimento": round(sent, 2),
        "impacto": grau_impacto(texto, n_afetados) if idioma == "pt" else "baixo",
        "beneficiados": impacto["beneficiados"],
        "prejudicados": impacto["prejudicados"],
        "setores": impacto["temas"],
        "renda_fixa": impacto["renda_fixa"],
        "fonte": "rss" if origem == "RSS" else "api",
        "origem": origem,
    }


def _ler_rss(url: str, limite: int = 15) -> list[dict[str, Any]]:
    resp = requests.get(url, timeout=6, headers={"User-Agent": "AlphaRadarB3/1.0"})
    resp.raise_for_status()
    itens = []
    for item in ET.fromstring(resp.content).iter("item"):
        titulo = (item.findtext("title") or "").strip()
        resumo = re.sub(r"<[^>]+>", "", item.findtext("description") or "").strip()[:400]
        data_txt = item.findtext("pubDate") or ""
        try:
            data_iso = parsedate_to_datetime(data_txt).isoformat()
        except (TypeError, ValueError):
            data_iso = data_txt
        novo = _montar_item(titulo, resumo, data_iso, item.findtext("link"), "RSS")
        if novo:
            itens.append(novo)
        if len(itens) >= limite:
            break
    return itens


def _ler_apis() -> list[dict[str, Any]]:
    itens = []
    for cru in news_apis.coletar():
        novo = _montar_item(cru["titulo"], cru["resumo"], cru["data"], cru["link"], cru["origem"], cru["idioma"], cru["filtrar"])
        if novo:
            itens.append(novo)
    return itens


def _buscar_rss_e_fallback() -> list[dict[str, Any]]:
    noticias: list[dict[str, Any]] = []
    urls = [u.strip() for u in os.getenv("NEWS_RSS_URLS", "").split(",") if u.strip()]
    if urls and not market_service.modo_offline():
        for url in urls:
            try:
                noticias.extend(_ler_rss(url))
            except Exception as erro:  # noqa: BLE001
                logger.warning("RSS indisponível (%s): %s", url, erro)
    if not market_service.modo_offline():
        noticias.extend(_ler_apis())
    if noticias:
        # Mesma manchete em feeds diferentes aparece uma vez só; mantém as 40 mais recentes.
        unicas = {n["id"]: n for n in noticias}
        return sorted(unicas.values(), key=lambda n: str(n.get("data", "")), reverse=True)[:40]
    for n in market_service.carregar_fallback()["noticias"]:
        n["fonte"] = "demonstracao"
        noticias.append(n)
    return noticias


def _carregar_bruto() -> list[dict[str, Any]]:
    """
    Notícias com cache curto (NEWS_CACHE_SECONDS, padrão 120 s): o feed "quase
    em tempo real" sem refazer a leitura dos RSS a cada clique do usuário.
    """
    ttl = float(os.getenv("NEWS_CACHE_SECONDS", "120") or 120)
    return copy.deepcopy(market_service._cache.obter_ou_calcular("noticias", ttl, _buscar_rss_e_fallback))


def feed_noticias() -> list[dict[str, Any]]:
    """Feed enriquecido: rótulo de sentimento, temas detectados e nomes dos ativos."""
    nomes = {a["ticker"]: a["nome"] for a in market_service.carregar_fallback()["ativos"]}
    feed = []
    for n in _carregar_bruto():
        texto = f"{n['titulo']}. {n.get('resumo', '')}"
        detectado = mapear_impacto(texto)
        n["sentimento_rotulo"] = rotulo_sentimento(float(n.get("sentimento", 0)))
        n["temas_detectados"] = detectado["temas"]
        n["ativos_afetados"] = [
            {"ticker": t, "nome": nomes.get(t, t), "efeito": "beneficiado"} for t in n.get("beneficiados", [])
        ] + [
            {"ticker": t, "nome": nomes.get(t, t), "efeito": "prejudicado"} for t in n.get("prejudicados", [])
        ]
        feed.append(n)
    feed.sort(key=lambda x: str(x.get("data", "")), reverse=True)
    return feed


def sentimento_por_ativo() -> dict[str, float]:
    """
    Índice de sentimento (-1 a +1) de cada ativo, somando o efeito das notícias:
        beneficiado -> +peso do impacto | prejudicado -> −peso do impacto
    A soma passa por tanh() para ficar sempre entre -1 e +1.
    """
    soma: dict[str, float] = {}
    for n in feed_noticias():
        peso = PESO_IMPACTO.get(n.get("impacto", "baixo"), 0.3)
        for t in n.get("beneficiados", []):
            soma[t] = soma.get(t, 0.0) + peso
        for t in n.get("prejudicados", []):
            soma[t] = soma.get(t, 0.0) - peso
    return {t: round(math.tanh(v / 1.5), 3) for t, v in soma.items()}


def noticias_do_ativo(ticker: str) -> list[dict[str, Any]]:
    ticker = ticker.upper()
    return [
        {**n, "efeito_no_ativo": "beneficiado" if ticker in n.get("beneficiados", []) else "prejudicado"}
        for n in feed_noticias()
        if ticker in n.get("beneficiados", []) or ticker in n.get("prejudicados", [])
    ]


def resumo_radar() -> dict[str, Any]:
    """Estatísticas do radar: contagem por sentimento e ativos mais citados."""
    feed = feed_noticias()
    contagem = {"Positivo": 0, "Neutro": 0, "Negativo": 0}
    for n in feed:
        contagem[n["sentimento_rotulo"]] += 1
    sent = sentimento_por_ativo()
    ranking = sorted(sent.items(), key=lambda kv: kv[1], reverse=True)
    return {
        "total": len(feed),
        "por_sentimento": contagem,
        "mais_beneficiados": [{"ticker": t, "indice": v} for t, v in ranking[:5] if v > 0],
        "mais_prejudicados": [{"ticker": t, "indice": v} for t, v in ranking[::-1][:5] if v < 0],
    }
