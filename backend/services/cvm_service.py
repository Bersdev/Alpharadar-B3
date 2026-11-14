"""
cvm_service.py — Comunicados oficiais das companhias abertas (dados abertos da CVM)
=====================================================================================

A CVM (Comissão de Valores Mobiliários) publica, em ``dados.cvm.gov.br``, todos os documentos que as
empresas listadas enviam ao mercado (conjunto "IPE"): Fatos Relevantes, Comunicados ao Mercado e Avisos
aos Acionistas. É a fonte OFICIAL: a notícia de jornal costuma ser a repercussão deste documento.

Como funciona:
    1. Baixa o arquivo do ano (``ipe_cia_aberta_AAAA.zip``, ~2 MB) e lê o CSV em memória.
    2. Mantém só as categorias que mexem com o preço e só as empresas que o app monitora
       (mapa ticker -> código CVM em ``CODIGOS_CVM``).
    3. Guarda em cache (30 min): o arquivo é atualizado algumas vezes ao dia, não a cada clique.

Segurança (a fonte é externa, então tratamos como dado não confiável):
    - Download com teto de tamanho; descompressão com teto (defesa contra "zip bomb").
    - O link do documento só é aceito se for https e do domínio da CVM; senão é descartado.
    - Textos são limpos e truncados antes de ir para a tela.
"""

from __future__ import annotations

import csv
import io
import logging
import os
import zipfile
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse

from services import market_service
from services.http_seguro import baixar

logger = logging.getLogger("alpharadar.cvm")

URL_IPE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/IPE/DADOS/ipe_cia_aberta_{ano}.zip"
LIMITE_ZIP = 8_000_000          # bytes baixados (o arquivo do ano tem ~2 MB)
LIMITE_CSV = 60_000_000         # bytes depois de descompactar
CACHE_SEGUNDOS = 1800
JANELA_DIAS = 90
DOMINIOS_CVM = ("cvm.gov.br",)

# Categorias que interessam a quem acompanha o preço de uma ação.
CATEGORIAS: dict[str, str] = {
    "Fato Relevante": "alto",
    "Comunicado ao Mercado": "medio",
    "Aviso aos Acionistas": "medio",
}

# ticker (B3) -> código CVM da companhia. FIIs e ativos dos EUA não são companhias abertas da CVM.
# Conferido no cadastro oficial (cad_cia_aberta.csv): companhias ativas negociadas em bolsa.
CODIGOS_CVM: dict[str, int] = {
    "BBAS3": 1023, "PETR4": 9512, "VALE3": 4170, "ITUB4": 19348, "WEGE3": 5410, "TAEE11": 20257,
    "BBSE3": 23159, "EGIE3": 17329, "PRIO3": 22187, "SUZB3": 13986, "RENT3": 19739, "RADL3": 5258,
    "ITSA4": 7617, "BBDC4": 906, "ABEV3": 23264, "B3SA3": 21610, "SANB11": 20532, "CMIG4": 2453,
    "VIVT3": 17671, "KLBN11": 12653, "GGBR4": 3980, "EQTL3": 20010, "LREN3": 8133, "MGLU3": 22470,
    "SAPR11": 18627, "CXSE3": 23795, "TIMS3": 24929, "CSAN3": 19836, "CPFE3": 18660, "ALUP11": 21490,
}
_TICKER_POR_CODIGO = {codigo: ticker for ticker, codigo in CODIGOS_CVM.items()}


def _link_da_cvm(link: str) -> str | None:
    """Só https e só domínio da CVM: o link vai para um <a href> e não pode ser um 'javascript:' nem outro site."""
    try:
        p = urlparse(link.strip())
    except ValueError:
        return None
    host = (p.hostname or "").lower()
    if p.scheme != "https" or not any(host == d or host.endswith("." + d) for d in DOMINIOS_CVM):
        return None
    return link.strip()


def _ler_ano(ano: int, desde: date) -> list[dict[str, Any]]:
    """Baixa e filtra o arquivo IPE de um ano. Levanta exceção se a fonte falhar (quem chama decide)."""
    bruto = baixar(URL_IPE.format(ano=ano), timeout=20, max_bytes=LIMITE_ZIP, headers={"User-Agent": "AlphaRadarB3/1.0"})
    with zipfile.ZipFile(io.BytesIO(bruto)) as arquivo:
        nomes = [n for n in arquivo.namelist() if n.lower().endswith(".csv")]
        if not nomes:
            raise ValueError("arquivo IPE sem CSV")
        with arquivo.open(nomes[0]) as f:
            texto = f.read(LIMITE_CSV + 1)
    if len(texto) > LIMITE_CSV:
        raise ValueError("CSV da CVM maior que o permitido")
    itens: list[dict[str, Any]] = []
    leitor = csv.DictReader(io.StringIO(texto.decode("latin-1")), delimiter=";")
    for linha in leitor:
        try:
            ticker = _TICKER_POR_CODIGO.get(int(linha["Codigo_CVM"]))
        except (KeyError, ValueError):
            continue
        categoria = linha.get("Categoria", "")
        if ticker is None or categoria not in CATEGORIAS:
            continue
        data_txt = (linha.get("Data_Entrega") or linha.get("Data_Referencia") or "")[:10]
        try:
            if date.fromisoformat(data_txt) < desde:
                continue
        except ValueError:
            continue
        link = _link_da_cvm(linha.get("Link_Download", ""))
        assunto = " ".join((linha.get("Assunto") or linha.get("Especie") or "").split())[:200]
        itens.append({
            "ticker": ticker,
            "empresa": " ".join((linha.get("Nome_Companhia") or "").split())[:80],
            "categoria": categoria,
            "assunto": assunto,
            "data": data_txt,
            "link": link,
            "protocolo": (linha.get("Protocolo_Entrega") or "")[:40],
        })
    return itens


def _buscar() -> list[dict[str, Any]]:
    """Documentos recentes (últimos 90 dias), do mais novo para o mais antigo. Vazio se a CVM estiver fora do ar."""
    if market_service.modo_offline() or os.getenv("CVM_DESLIGADA", "").lower() in ("1", "true", "sim"):
        return []
    hoje = date.today()
    desde = hoje - timedelta(days=JANELA_DIAS)
    anos = sorted({hoje.year, desde.year})
    todos: list[dict[str, Any]] = []
    falhas = 0
    for ano in anos:
        try:
            todos.extend(_ler_ano(ano, desde))
        except Exception as erro:  # noqa: BLE001 — a CVM fora do ar não pode derrubar o app
            falhas += 1
            logger.warning("CVM indisponível (%s): %s", ano, type(erro).__name__)
    if falhas == len(anos):
        raise ConnectionError("CVM indisponível")
    vistos: set[str] = set()
    unicos = []
    for it in sorted(todos, key=lambda x: x["data"], reverse=True):
        chave = it["protocolo"] or f"{it['ticker']}{it['data']}{it['assunto']}"
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(it)
    return unicos


def documentos_recentes() -> list[dict[str, Any]]:
    try:
        return list(market_service._cache.obter_ou_calcular("cvm_ipe", CACHE_SEGUNDOS, _buscar))
    except Exception:  # noqa: BLE001
        # CVM fora do ar: lista vazia, lembrada por 2 min (não refaz um download de 20 s a cada pedido).
        return list(market_service._cache.obter_ou_calcular("cvm_falha", 120, list))


def comunicados_do_ativo(ticker: str, limite: int = 8) -> list[dict[str, Any]]:
    """Comunicados oficiais da empresa (vazio para FIIs e ativos dos EUA)."""
    ticker = ticker.upper()
    if ticker not in CODIGOS_CVM:
        return []
    return [d for d in documentos_recentes() if d["ticker"] == ticker][:limite]


def titulo_do_documento(doc: dict[str, Any]) -> str:
    return f"{doc['categoria']} — {doc['empresa'] or doc['ticker']}: {doc['assunto'] or 'sem assunto informado'}"


def noticias_oficiais(limite: int = 10) -> list[dict[str, Any]]:
    """Fatos Relevantes mais recentes, em formato bruto para o radar de notícias."""
    fatos = [d for d in documentos_recentes() if d["categoria"] == "Fato Relevante"]
    return fatos[:limite]
