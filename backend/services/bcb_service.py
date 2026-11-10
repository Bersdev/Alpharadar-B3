"""
bcb_service.py — Indicadores macro do Banco Central do Brasil
===============================================================

Busca Selic, CDI e IPCA na API pública SGS (Sistema Gerenciador de Séries
Temporais) do Banco Central: https://dadosabertos.bcb.gov.br/

Usamos a API REST diretamente com ``requests`` — é a mesma API que a
biblioteca ``python-bcb`` encapsula, mas assim o projeto não depende de mais
um pacote e o funcionamento fica transparente para estudo.

Formato da URL:
    https://api.bcb.gov.br/dados/serie/bcdata.sgs.{CODIGO}/dados/ultimos/1?formato=json

Resposta típica:
    [{"data": "06/11/2026", "valor": "15.00"}]

Séries utilizadas:
    432   -> Meta da Taxa Selic definida pelo Copom (% a.a.)
    4389  -> CDI anualizado base 252 dias úteis (% a.a.)
    13522 -> IPCA acumulado em 12 meses (%)
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger("alpharadar.bcb")

URL_SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json"
TIMEOUT_SEGUNDOS = 6

SERIES_SGS: dict[str, int] = {
    "selic_anual": 432,
    "cdi_anual": 4389,
    "ipca_12m": 13522,
}


def buscar_serie(codigo: int) -> tuple[float, str]:
    """
    Busca o ÚLTIMO valor de uma série do SGS.

    Retorna ``(valor, data)``. Lança exceção se a API falhar — quem chama
    (``market_service``) é responsável por cair no fallback.
    """
    resposta = requests.get(
        URL_SGS.format(codigo=codigo),
        timeout=TIMEOUT_SEGUNDOS,
        headers={"Accept": "application/json", "User-Agent": "AlphaRadarB3/1.0"},
    )
    resposta.raise_for_status()               # erro HTTP (4xx/5xx) vira exceção
    dados = resposta.json()
    ultimo = dados[-1]
    return float(ultimo["valor"]), str(ultimo["data"])


def buscar_indicadores_macro() -> dict[str, float | str]:
    """
    Busca Selic, CDI e IPCA de uma vez.

    Se UMA série falhar, as outras continuam valendo; a que falhou fica de
    fora do dicionário e o ``market_service`` completa com o fallback.
    """
    resultado: dict[str, float | str] = {}
    for nome, codigo in SERIES_SGS.items():
        try:
            valor, data = buscar_serie(codigo)
            resultado[nome] = valor
            resultado[f"{nome}_data"] = data
        except Exception as erro:  # noqa: BLE001 — resiliência acima de tudo
            logger.warning("SGS %s (%s) indisponível: %s", nome, codigo, erro)
    return resultado
