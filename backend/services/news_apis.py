"""
news_apis.py — Fontes de notícias por API (opcionais)
=======================================================

Cada fonte só é consultada se a chave correspondente existir no ``.env``.
Todas devolvem uma lista de dicionários "crus":

    {"titulo", "resumo", "data" (ISO), "link", "origem", "idioma", "filtrar"}

e o ``news_service`` aplica sentimento, cadeia de impacto e filtro de mercado.
Uma fonte que falhar (chave inválida, limite diário) é ignorada com um aviso
no log — o radar continua com as demais.

Fontes e o que valem para este projeto (limites do plano gratuito):

    Currents API   (CURRENTS_API_KEY)  250 req/dia, em tempo real, filtra Brasil + português
                                       -> a melhor fonte por API para a B3
    GNews          (GNEWS_API_KEY)     100 req/dia, 10 notícias/req, filtro por país/idioma,
                                       mas o plano gratuito tem atraso de ~12 h
    The Guardian   (GUARDIAN_API_KEY)  tempo real, seção "business", em inglês -> contexto global
    New York Times (NYT_API_KEY)       Top Stories de negócios, em inglês -> contexto global
    NewsAPI.org    (NEWSAPI_KEY)       100 req/dia, atraso de 24 h e uso só em desenvolvimento
                                       (proibido em produção no plano gratuito) -> pouco útil
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

import requests

logger = logging.getLogger("alpharadar.newsapis")

TIMEOUT = 8
HEADERS = {"User-Agent": "AlphaRadarB3/1.0"}

# Busca focada em mercado brasileiro (sintaxe de busca simples com OR).
CONSULTA_PT = "Selic OR Copom OR Ibovespa OR dólar OR dividendos OR \"fundos imobiliários\" OR Petrobras OR Vale OR inflação"


def _chave(nome: str) -> str:
    return os.getenv(nome, "").strip()


def _get(url: str, **kwargs: Any) -> Any:
    resp = requests.get(url, timeout=TIMEOUT, headers={**HEADERS, **kwargs.pop("headers", {})}, **kwargs)
    resp.raise_for_status()
    return resp.json()


def _item(titulo: str | None, resumo: str | None, data: str | None, link: str | None,
          origem: str, idioma: str, filtrar: bool) -> dict[str, Any] | None:
    if not titulo:
        return None
    return {
        "titulo": titulo.strip(),
        "resumo": (resumo or "").strip()[:400],
        "data": data or "",
        "link": link,
        "origem": origem,
        "idioma": idioma,
        "filtrar": filtrar,
    }


# --------------------------- Fontes em português ---------------------------

def currents() -> list[dict[str, Any]]:
    dados = _get(
        "https://api.currentsapi.services/v1/search",
        params={"keywords": CONSULTA_PT, "language": "pt", "country": "BR", "page_size": 20},
        headers={"Authorization": f"Bearer {_chave('CURRENTS_API_KEY')}"},
    )
    return [i for a in dados.get("news", []) if (i := _item(
        a.get("title"), a.get("description"), a.get("published"), a.get("url"), "Currents", "pt", True))]


def gnews() -> list[dict[str, Any]]:
    dados = _get(
        "https://gnews.io/api/v4/search",
        params={"q": CONSULTA_PT, "lang": "pt", "country": "br", "max": 10, "apikey": _chave("GNEWS_API_KEY")},
    )
    return [i for a in dados.get("articles", []) if (i := _item(
        a.get("title"), a.get("description"), a.get("publishedAt"), a.get("url"), "GNews", "pt", True))]


def newsapi() -> list[dict[str, Any]]:
    dados = _get(
        "https://newsapi.org/v2/top-headlines",
        params={"country": "br", "category": "business", "pageSize": 20},
        headers={"X-Api-Key": _chave("NEWSAPI_KEY")},
    )
    return [i for a in dados.get("articles", []) if (i := _item(
        a.get("title"), a.get("description"), a.get("publishedAt"), a.get("url"), "NewsAPI", "pt", True))]


# ---------------------------- Fontes em inglês -----------------------------

def guardian() -> list[dict[str, Any]]:
    dados = _get(
        "https://content.guardianapis.com/search",
        params={"section": "business", "order-by": "newest", "page-size": 15,
                "show-fields": "trailText", "api-key": _chave("GUARDIAN_API_KEY")},
    )
    return [i for a in dados.get("response", {}).get("results", []) if (i := _item(
        a.get("webTitle"), (a.get("fields") or {}).get("trailText"), a.get("webPublicationDate"),
        a.get("webUrl"), "The Guardian", "en", False))]


def nytimes() -> list[dict[str, Any]]:
    dados = _get(
        "https://api.nytimes.com/svc/topstories/v2/business.json",
        params={"api-key": _chave("NYT_API_KEY")},
    )
    return [i for a in dados.get("results", [])[:15] if (i := _item(
        a.get("title"), a.get("abstract"), a.get("published_date"), a.get("url"), "The New York Times", "en", False))]


FONTES: list[tuple[str, str, Callable[[], list[dict[str, Any]]]]] = [
    ("CURRENTS_API_KEY", "Currents", currents),
    ("GNEWS_API_KEY", "GNews", gnews),
    ("NEWSAPI_KEY", "NewsAPI", newsapi),
    ("GUARDIAN_API_KEY", "Guardian", guardian),
    ("NYT_API_KEY", "NYT", nytimes),
]


def fontes_ativas() -> list[str]:
    return [nome for env, nome, _ in FONTES if _chave(env)]


def coletar() -> list[dict[str, Any]]:
    """Consulta todas as fontes que têm chave configurada; erros de uma não afetam as outras."""
    itens: list[dict[str, Any]] = []
    for env, nome, buscar in FONTES:
        if not _chave(env):
            continue
        try:
            itens.extend(buscar())
        except Exception as erro:  # noqa: BLE001
            # Nunca imprimir a URL: ela pode conter a chave (?apikey=...).
            logger.warning("%s indisponível: %s", nome, type(erro).__name__)
    return itens
