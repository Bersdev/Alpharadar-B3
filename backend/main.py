"""
main.py — Servidor FastAPI do AlphaRadar B3
=============================================

Como rodar (dentro da pasta backend/):
    uvicorn main:app --reload --port 8000

Documentação interativa gerada automaticamente:
    http://localhost:8000/docs    (Swagger UI — teste todas as rotas com um clique)
    http://localhost:8000/redoc   (documentação em formato de leitura)

Arquitetura em camadas:
    main.py (rotas HTTP)
       └── engine/   (regras de negócio e matemática: valuation, renda fixa, IA)
       └── services/ (coleta de dados: B3, Banco Central, notícias + fallback)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv()  # lê backend/.env (se existir) ANTES de importar os serviços

from engine import ai_analyst, fixed_income, valuation  # noqa: E402
from services import global_service, market_service, news_service  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("alpharadar.api")

@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    """Ao iniciar, aquece os caches (cotações, fundamentos e mercado global) em segundo plano:
    o primeiro visitante não espera as dezenas de consultas ao Yahoo."""
    def _aquecer() -> None:
        for tarefa in (market_service.listar_ativos, global_service.panorama_global, global_service.expectativas_focus):
            try:
                tarefa()
            except Exception as erro:  # noqa: BLE001
                logger.warning("Aquecimento de %s falhou: %s", tarefa.__name__, type(erro).__name__)

    threading.Thread(target=_aquecer, daemon=True).start()
    yield


app = FastAPI(
    lifespan=ciclo_de_vida,
    title="AlphaRadar B3 API",
    version="1.0.0",
    description=(
        "Motor financeiro em Python do AlphaRadar B3: Preço-Teto (Bazin histórico e projetivo), "
        "Preço Justo de Graham, Score Alpha (0–100), simulador de LCI/LCA/CDB/Tesouro, radar de "
        "notícias com cadeia de impacto e analista de IA. Conteúdo educativo — não é recomendação "
        "de investimento."
    ),
)

# CORS: só o seu site (e o ambiente local) podem ler a API pelo navegador de um visitante.
# A demonstração pública já vem liberada; num fork, defina CORS_ORIGINS com o endereço do seu site
# (várias URLs separadas por vírgula).
# Importante: CORS protege o NAVEGADOR do visitante; quem chama a API direto (curl) não é afetado por ele.
SITE_DA_DEMONSTRACAO = "https://alpharadar-b3.up.railway.app"
ORIGENS_PERMITIDAS = ["http://localhost:3000", "http://127.0.0.1:3000", SITE_DA_DEMONSTRACAO] + [
    o.strip().rstrip("/") for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENS_PERMITIDAS,
    allow_methods=["GET", "POST", "OPTIONS"],  # a API não tem escrita: nada de PUT/DELETE/PATCH
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def cabecalhos_de_seguranca(request: Request, call_next):
    """Cabeçalhos que endurecem o navegador de quem consome a API (e a documentação em /docs)."""
    resposta = await call_next(request)
    resposta.headers.setdefault("X-Content-Type-Options", "nosniff")
    resposta.headers.setdefault("Referrer-Policy", "no-referrer")
    resposta.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    if not request.url.path.startswith(("/docs", "/redoc")):  # o Swagger precisa de recursos externos
        resposta.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        resposta.headers.setdefault("X-Frame-Options", "DENY")
    return resposta


# Limite de uso da rota de IA (por IP): em um site público, sem isso qualquer pessoa
# poderia esgotar a cota gratuita do provedor de IA.
LIMITE_IA_POR_MINUTO = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "8"))      # por IP
LIMITE_IA_GLOBAL_POR_MINUTO = int(os.getenv("AI_GLOBAL_RATE_LIMIT_PER_MINUTE", "60"))  # todos juntos
MAX_IPS_RASTREADOS = 5000
_acessos_ia: "OrderedDict[str, list[float]]" = OrderedDict()
_acessos_globais: list[float] = []
_trava_limite = threading.Lock()  # a rota roda em várias threads: leitura, checagem e escrita são uma operação só


def _ip_do_cliente(request: Request) -> str:
    """
    IP do visitante. Atrás de um proxy (como o da Railway), o IP real é ACRESCENTADO ao fim de
    X-Forwarded-For; os endereços anteriores são escritos pelo próprio cliente e podem ser
    falsificados, então usamos o último. Sem o cabeçalho (rodando localmente), vale o IP da conexão.
    Sem proxy confiável na frente, o cabeçalho poderia ser forjado: por isso o teto GLOBAL também existe.
    """
    encaminhado = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if encaminhado:
        return encaminhado[-1]
    return request.client.host if request.client else "desconhecido"


def _checar_limite_ia(request: Request) -> None:
    agora = time.time()
    ip = _ip_do_cliente(request)
    with _trava_limite:
        # Teto global: mesmo quem consiga trocar de IP não passa deste total por minuto.
        _acessos_globais[:] = [t for t in _acessos_globais if agora - t < 60]
        recentes = [t for t in _acessos_ia.get(ip, []) if agora - t < 60]
        if len(recentes) >= LIMITE_IA_POR_MINUTO or len(_acessos_globais) >= LIMITE_IA_GLOBAL_POR_MINUTO:
            raise HTTPException(status_code=429, detail="Muitas perguntas seguidas. Aguarde um minuto e tente de novo.")
        recentes.append(agora)
        _acessos_globais.append(agora)
        _acessos_ia[ip] = recentes
        _acessos_ia.move_to_end(ip)
        while len(_acessos_ia) > MAX_IPS_RASTREADOS:  # descarta os IPs menos recentes (LRU)
            _acessos_ia.popitem(last=False)


@app.exception_handler(Exception)
async def erro_inesperado(_: Request, erro: Exception) -> JSONResponse:
    """Rede de segurança: qualquer erro não tratado vira uma resposta amigável."""
    logger.exception("Erro inesperado: %s", erro)
    return JSONResponse(
        status_code=503,
        content={"erro": "Serviço temporariamente indisponível. Tente novamente em instantes."},
    )


# ---------------------------------------------------------------------------
# Modelos de entrada (Pydantic valida tipos e limites automaticamente)
# ---------------------------------------------------------------------------

class SimulacaoValuation(BaseModel):
    ticker: str | None = Field(None, description="Se vazio, recalcula todos os ativos.")
    yield_desejado: float | None = Field(None, ge=0.01, le=0.30, description="Ex.: 0.08 = 8% a.a. Vazio = 6% ações / 8% FIIs.")
    crescimento_g: float | None = Field(None, ge=-0.5, le=1.0, description="Ex.: 0.05 = 5%. Vazio = usa o do ativo.")
    payout_pct: float | None = Field(None, ge=0, le=100, description="Ex.: 60 = 60%. Vazio = usa o médio do ativo.")


class SimulacaoRendaFixa(BaseModel):
    valor_inicial: float = Field(10_000, ge=0, le=1e9)
    aporte_mensal: float = Field(0, ge=0, le=1e8)
    meses: int = Field(24, ge=1, le=360)
    cdi_anual: float | None = Field(None, ge=0, le=1, description="Vazio = CDI atual do Banco Central.")
    selic_anual: float | None = Field(None, ge=0, le=1, description="Vazio = Selic atual do Banco Central.")
    taxa_lci_pct_cdi: float = Field(92, ge=0, le=200)
    taxa_lca_pct_cdi: float = Field(90, ge=0, le=200)
    taxa_cdb_pct_cdi: float = Field(105, ge=0, le=200)
    dy_dividendos_anual: float = Field(0.11, ge=0, le=1)


class PerguntaIA(BaseModel):
    pergunta: str = Field("", max_length=1000)
    ticker: str | None = None


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _ativos_avaliados(**premissas: Any) -> list[dict[str, Any]]:
    """Junta dados do ativo + resultado do motor de valuation."""
    sent = news_service.sentimento_por_ativo()
    saida = []
    for ativo in market_service.listar_ativos()["ativos"]:
        av = valuation.avaliar_ativo(ativo, sentimento_noticias=sent.get(ativo["ticker"], 0.0), **premissas)
        saida.append({**ativo, **av, "sentimento_noticias": sent.get(ativo["ticker"], 0.0)})
    return saida


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------

@app.get("/", tags=["Sistema"])
def raiz() -> dict[str, str]:
    return {"projeto": "AlphaRadar B3", "docs": "/docs", "status": "ok"}


@app.get("/api/health", tags=["Sistema"])
def saude() -> dict[str, Any]:
    return {
        "status": "ok",
        "modo_offline": market_service.modo_offline(),
        "ia_generativa": ai_analyst.llm_disponivel(),
        "ia_provedor": ai_analyst.provedor_ia(),
        "ia_provedores": ai_analyst.provedores_ativos(),
    }


@app.get("/api/overview", tags=["Mercado"])
def visao_geral() -> dict[str, Any]:
    """Pulso do mercado: macro Brasil/Mundo, altas e baixas, cenário Bolsa × LCI/LCA e manchetes."""
    macro = market_service.indicadores_macro()
    lista = market_service.listar_ativos()
    ativos = lista["ativos"]
    ordenados = sorted(ativos, key=lambda a: a["variacao_dia"], reverse=True)
    resumo_ativo = lambda a: {k: a[k] for k in ("ticker", "nome", "tipo", "mercado", "moeda", "cotacao", "variacao_dia")}  # noqa: E731

    # Cenário: quanto rende a renda fixa isenta frente aos dividendos da bolsa?
    cdi = macro["cdi_anual"]
    lci_92 = cdi * 0.92
    avaliados = _ativos_avaliados()
    dy_fiis = [a["dy_projetado"] for a in avaliados if a["tipo"] == "fii" and a["dy_projetado"]]
    dy_acoes = [a["dy_projetado"] for a in avaliados if a["tipo"] == "acao" and a["mercado"] == "B3" and a["dy_projetado"]]
    dy_medio_fii = sum(dy_fiis) / len(dy_fiis) if dy_fiis else 0
    dy_medio_acao = sum(dy_acoes) / len(dy_acoes) if dy_acoes else 0
    if macro["juro_real"] >= 6:
        leitura = ("Juro real muito alto: LCI/LCA isentas pagam quase o mesmo que os dividendos, sem risco de bolsa. "
                   "Para ações e FIIs, exija margem de segurança maior.")
    elif macro["juro_real"] >= 3:
        leitura = "Juro real moderado: equilíbrio entre renda fixa e bolsa; diversificação é o caminho."
    else:
        leitura = "Juro real baixo: a renda fixa perde atratividade e a bolsa tende a ganhar fluxo."

    noticias = news_service.feed_noticias()
    return {
        "macro": macro,
        "fonte_cotacoes": lista["fonte"],
        "atualizado_em": lista["atualizado_em"],
        "maiores_altas": [resumo_ativo(a) for a in ordenados[:5]],
        "maiores_baixas": [resumo_ativo(a) for a in ordenados[::-1][:5]],
        "cenario": {
            "lci_92_cdi": round(lci_92, 2),
            "cdb_equivalente_lci_92": round(fixed_income.taxa_cdb_equivalente(92, 721), 2),
            "dy_medio_fiis": round(dy_medio_fii, 2),
            "dy_medio_acoes": round(dy_medio_acao, 2),
            "premio_fii_vs_lci": round(dy_medio_fii - lci_92, 2),
            "leitura": leitura,
        },
        "manchetes_urgentes": [n for n in noticias if n.get("impacto") == "alto"][:4],
        "ticker_tape": [resumo_ativo(a) for a in ativos],
    }


@app.get("/api/mercado", tags=["Mercado"])
def mercado_global() -> dict[str, Any]:
    """Bolsas, moedas, cripto, commodities, juros dos EUA, termômetro de risco e série juros × Ibovespa."""
    return global_service.panorama_global()


@app.get("/api/macro", tags=["Mercado"])
def macro_e_agenda() -> dict[str, Any]:
    """Expectativas do Boletim Focus (Selic, IPCA, PIB, câmbio) e agenda econômica da semana."""
    return {"focus": global_service.expectativas_focus(), "agenda": global_service.agenda_economica()}


@app.get("/api/assets", tags=["Ativos"])
def listar_ativos(
    tipo: str | None = Query(None, pattern="^(acao|fii)$"),
    mercado: str | None = Query(None, pattern="^(B3|EUA)$"),
    yield_desejado: float | None = Query(None, ge=0.01, le=0.30, description="Vazio = 6% ações / 8% FIIs"),
) -> dict[str, Any]:
    """Ações e FIIs já calculados: Score Alpha, Preço-Teto Bazin, Projetivo e Graham."""
    ativos = _ativos_avaliados(yield_desejado=yield_desejado)
    if tipo:
        ativos = [a for a in ativos if a["tipo"] == tipo]
    if mercado:
        ativos = [a for a in ativos if a["mercado"] == mercado]
    ativos.sort(key=lambda a: a["score"]["total"], reverse=True)
    return {"ativos": ativos, "total": len(ativos), "fonte": market_service.listar_ativos()["fonte"]}


@app.get("/api/assets/{ticker}", tags=["Ativos"])
def detalhe_ativo(ticker: str) -> dict[str, Any]:
    """Raio-X do ativo: histórico de preços, dividendos, score detalhado, risco e notícias."""
    ativo = market_service.obter_ativo(ticker)
    if ativo is None:
        raise HTTPException(status_code=404, detail=f"Ativo {ticker.upper()} não é monitorado pelo AlphaRadar.")
    sent = news_service.sentimento_por_ativo().get(ativo["ticker"], 0.0)
    hist = market_service.historico_ativo(ativo["ticker"])
    macro = market_service.indicadores_macro()
    av = valuation.avaliar_ativo(ativo, sentimento_noticias=sent)
    return {
        "ativo": ativo,
        "valuation": av,
        "historico": hist,
        "risco": market_service.estatisticas_risco(hist["precos"]),
        "premio_lci": fixed_income.premio_de_risco(av["dy_projetado"] or 0, 92, macro["cdi_anual"] / 100, ativo["mercado"]),
        "noticias": news_service.noticias_do_ativo(ativo["ticker"]),
        "sentimento_noticias": sent,
    }


@app.post("/api/simulate/valuation", tags=["Simuladores"])
def simular_valuation(body: SimulacaoValuation) -> dict[str, Any]:
    """Recalcula Preço-Teto Projetivo, margens e Score com as premissas dos sliders."""
    premissas = {"yield_desejado": body.yield_desejado, "crescimento_g": body.crescimento_g, "payout_pct": body.payout_pct}
    if body.ticker:
        ativo = market_service.obter_ativo(body.ticker)
        if ativo is None:
            raise HTTPException(status_code=404, detail=f"Ativo {body.ticker.upper()} não encontrado.")
        sent = news_service.sentimento_por_ativo().get(ativo["ticker"], 0.0)
        return {"resultados": [{**ativo, **valuation.avaliar_ativo(ativo, sentimento_noticias=sent, **premissas)}]}
    resultados = _ativos_avaliados(**premissas)
    resultados.sort(key=lambda a: a["score"]["total"], reverse=True)
    return {"resultados": resultados}


@app.post("/api/simulate/fixed-income", tags=["Simuladores"])
def simular_renda_fixa(body: SimulacaoRendaFixa) -> dict[str, Any]:
    """Simulação mês a mês de LCI/LCA × CDB × Tesouro Selic × dividendos reinvestidos."""
    macro = market_service.indicadores_macro()
    params = fixed_income.ParametrosSimulacao(
        valor_inicial=body.valor_inicial,
        aporte_mensal=body.aporte_mensal,
        meses=body.meses,
        cdi_anual=body.cdi_anual if body.cdi_anual is not None else macro["cdi_anual"] / 100,
        selic_anual=body.selic_anual if body.selic_anual is not None else macro["selic_anual"] / 100,
        taxa_lci_pct_cdi=body.taxa_lci_pct_cdi,
        taxa_lca_pct_cdi=body.taxa_lca_pct_cdi,
        taxa_cdb_pct_cdi=body.taxa_cdb_pct_cdi,
        dy_dividendos_anual=body.dy_dividendos_anual,
    )
    return fixed_income.simular_renda_fixa(params)


@app.get("/api/news-radar", tags=["Notícias"])
def radar_noticias(sentimento: str | None = Query(None, pattern="^(Positivo|Neutro|Negativo)$")) -> dict[str, Any]:
    """Feed de notícias com sentimento, grau de impacto e cadeia de ativos afetados."""
    feed = news_service.feed_noticias()
    if sentimento:
        feed = [n for n in feed if n["sentimento_rotulo"] == sentimento]
    return {"noticias": feed, "resumo": news_service.resumo_radar(), "sentimento_por_ativo": news_service.sentimento_por_ativo()}


@app.post("/api/ai/analyze", tags=["Inteligência Artificial"])
def analisar_ia(body: PerguntaIA, request: Request) -> dict[str, Any]:
    """Copiloto: risco, histórico, efeito de juros e comparações (motor de regras ou Claude)."""
    _checar_limite_ia(request)
    return ai_analyst.analisar(body.pergunta, body.ticker)
