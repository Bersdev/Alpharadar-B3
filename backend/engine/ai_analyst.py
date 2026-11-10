"""
ai_analyst.py — Copiloto de Análise do AlphaRadar B3
======================================================

Funciona em DOIS modos, escolhidos automaticamente:

1. Modo "regras" (padrão, gratuito, offline)
   Um motor analítico em Python que entende a intenção da pergunta
   (análise de um ativo, efeito da Selic, comparação LCI × FII...) e monta
   a resposta com os números calculados por ``valuation.py``,
   ``fixed_income.py`` e ``news_service.py``. É 100% determinístico e
   auditável — ótimo para explicar numa entrevista.

2. Modo "llm" (opcional)
   Se existir ``ANTHROPIC_API_KEY`` no .env, os MESMOS dados calculados são
   enviados ao Claude (SDK oficial da Anthropic), que redige uma análise em
   linguagem natural. O LLM recebe os números prontos: quem faz a conta é o
   Python, o modelo só interpreta. Se a chamada falhar por qualquer motivo,
   voltamos ao modo "regras" sem erro para o usuário.

Aviso: conteúdo educativo. Não é recomendação de investimento.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from typing import Any

from engine import fixed_income, valuation
from services import market_service, news_service

logger = logging.getLogger("alpharadar.ai")

AVISO_LEGAL = (
    "Conteúdo educativo gerado automaticamente a partir de dados públicos e premissas "
    "simplificadas. Não constitui recomendação de compra ou venda de ativos."
)
MODELO_PADRAO = "claude-opus-5-5"

PROMPT_SISTEMA = """Você é o analista educativo do AlphaRadar B3, um projeto de estudo sobre o mercado brasileiro.
Responda em português do Brasil, de forma clara e didática, para um investidor iniciante.
Regras:
- Use SOMENTE os números fornecidos no bloco DADOS (calculados pelo backend em Python). Não invente cotações, datas ou fatos.
- Explique o raciocínio (o que cada indicador significa e por que importa).
- Aponte pontos fortes e pontos de atenção/riscos.
- Não faça recomendação personalizada de compra ou venda; termine lembrando que o conteúdo é educativo.
- Definições corretas: Preço-Teto de Bazin usa os dividendos JÁ PAGOS; Preço-Teto Projetivo usa o dividendo ESTIMADO (LPA x crescimento x payout). P/VP abaixo de 1 significa cotação ABAIXO do valor patrimonial. Margem positiva = cotação abaixo do preço-alvo; negativa = acima.
- Formato: até 5 parágrafos curtos ou listas com marcadores "- ". Sem tabelas."""


# ---------------------------------------------------------------------------
# Utilidades de interpretação da pergunta
# ---------------------------------------------------------------------------

def _tickers_na_pergunta(pergunta: str) -> list[str]:
    conhecidos = set(market_service.tickers_monitorados())
    candidatos = re.findall(r"\b([A-Za-z]{4}\d{1,2})\b", pergunta)
    vistos: list[str] = []
    for c in candidatos:
        c = c.upper()
        if c in conhecidos and c not in vistos:
            vistos.append(c)
    return vistos


def _fmt_moeda(v: float | None) -> str:
    if v is None:
        return "n/d"
    return "R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_num(v: float | None, casas: int = 2) -> str:
    return "n/d" if v is None else f"{v:.{casas}f}".replace(".", ",")


def _fmt_pct(v: float | None, casas: int = 1) -> str:
    return "n/d" if v is None else f"{v:.{casas}f}%".replace(".", ",")


# ---------------------------------------------------------------------------
# Relatórios do motor de regras
# ---------------------------------------------------------------------------

def relatorio_ativo(ticker: str) -> dict[str, Any]:
    """Raio-X completo de um ativo: histórico, valuation, risco e notícias."""
    ativo = market_service.obter_ativo(ticker)
    if ativo is None:
        return {
            "titulo": f"Ativo {ticker} não monitorado",
            "resumo": "O AlphaRadar acompanha 16 ativos. Tente, por exemplo, BBAS3, PETR4 ou HGLG11.",
            "secoes": [],
            "ativos": [],
        }
    sent = news_service.sentimento_por_ativo().get(ativo["ticker"], 0.0)
    av = valuation.avaliar_ativo(ativo, sentimento_noticias=sent)
    hist = market_service.historico_ativo(ativo["ticker"])
    risco = market_service.estatisticas_risco(hist["precos"])
    noticias = news_service.noticias_do_ativo(ativo["ticker"])
    macro = market_service.indicadores_macro()
    premio = fixed_income.premio_de_risco(av["dy_projetado"] or 0, 92, macro["cdi_anual"] / 100)
    eh_fii = ativo.get("tipo") == "fii"

    fortes: list[str] = []
    atencao: list[str] = []
    if (av["margem_projetiva"] or -99) > 10:
        fortes.append(f"Cotação {_fmt_pct(av['margem_projetiva'])} abaixo do Preço-Teto Projetivo.")
    elif av["margem_projetiva"] is not None and av["margem_projetiva"] < -10:
        atencao.append(f"Cotação {_fmt_pct(abs(av['margem_projetiva']))} acima do Preço-Teto Projetivo.")
    if (av["dy_projetado"] or 0) >= 8:
        fortes.append(f"Dividend Yield projetado elevado ({_fmt_pct(av['dy_projetado'])}).")
    elif (av["dy_projetado"] or 0) < 4:
        atencao.append(f"Dividend Yield projetado baixo ({_fmt_pct(av['dy_projetado'])}): foco em crescimento, não em renda.")
    if not eh_fii and (ativo.get("roe") or 0) >= 18:
        fortes.append(f"Alta rentabilidade: ROE de {_fmt_pct(ativo['roe'])}.")
    if ativo.get("divida_liquida_ebitda") is not None and ativo["divida_liquida_ebitda"] >= 3:
        atencao.append(f"Endividamento relevante: Dívida Líquida/EBITDA de {_fmt_num(ativo['divida_liquida_ebitda'], 1)}x.")
    if (risco["volatilidade_anual"] or 0) > 35:
        atencao.append(f"Volatilidade alta ({_fmt_pct(risco['volatilidade_anual'])} ao ano).")
    if (risco["max_drawdown"] or 0) < -30:
        atencao.append(f"Queda máxima de {_fmt_pct(risco['max_drawdown'])} nos últimos 12 meses.")
    if premio["premio_pp"] < 0:
        atencao.append(premio["leitura"])
    elif premio["premio_pp"] >= 2:
        fortes.append(premio["leitura"])
    if sent > 0.2:
        fortes.append("Fluxo de notícias recente favorável.")
    elif sent < -0.2:
        atencao.append("Fluxo de notícias recente desfavorável.")

    secoes = [
        {"titulo": "Histórico (12 meses)", "itens": [
            f"Retorno da cotação no período: {_fmt_pct(risco['retorno_periodo'])}.",
            f"Proventos pagos nos últimos 12 meses: {_fmt_moeda(av['dpa_12m'])} por {'cota' if eh_fii else 'ação'} "
            f"(DY atual de {_fmt_pct(av['dy_atual'])}).",
            f"Fonte do histórico: {'dados ao vivo (Yahoo Finance)' if hist.get('fonte') == 'ao_vivo' else 'série ilustrativa offline'}.",
        ]},
        {"titulo": "Valuation", "itens": [
            f"Cotação atual: {_fmt_moeda(av['cotacao'])}.",
            f"Preço Justo de Graham: {_fmt_moeda(av['preco_justo_graham'])} (margem {_fmt_pct(av['margem_graham'])}).",
            f"Preço-Teto Bazin ({av['premissas']['yield_desejado'] * 100:.0f}% sobre dividendos passados): {_fmt_moeda(av['preco_teto_bazin'])}.",
            f"Preço-Teto Projetivo: {_fmt_moeda(av['preco_teto_projetivo'])} (margem {_fmt_pct(av['margem_projetiva'])}).",
            f"P/L de {_fmt_num(ativo.get('pl'), 1)} e P/VP de {_fmt_num(ativo.get('pvp'))}.",
        ]},
        {"titulo": "Risco", "itens": [
            f"Volatilidade anualizada: {_fmt_pct(risco['volatilidade_anual'])}; queda máxima: {_fmt_pct(risco['max_drawdown'])}.",
            f"Beta estimado: {_fmt_num(ativo.get('beta'))} (1,0 = oscila como o Ibovespa).",
            (f"Dívida Líquida/EBITDA: {_fmt_num(ativo['divida_liquida_ebitda'], 1)}x." if ativo.get("divida_liquida_ebitda") is not None
             else "Dívida/EBITDA não se aplica a este tipo de ativo."),
            f"Prêmio sobre LCI 92% do CDI: {_fmt_num(premio['premio_pp'])} p.p. {premio['leitura']}",
        ]},
        {"titulo": "Pontos fortes", "itens": fortes or ["Nenhum destaque positivo forte pelas regras atuais."]},
        {"titulo": "Pontos de atenção", "itens": atencao or ["Nenhum alerta relevante pelas regras atuais."]},
        {"titulo": "Notícias relacionadas", "itens": [
            f"[{n['efeito_no_ativo']}] {n['titulo']}" for n in noticias[:5]
        ] or ["Nenhuma notícia recente associada."]},
    ]
    score = av["score"]
    return {
        "titulo": f"Análise de {ativo['ticker']} — {ativo['nome']}",
        "resumo": (
            f"{ativo['nome']} ({ativo['setor']}) tem Score Alpha de {score['total']:.0f}/100 "
            f"({score['classificacao']}). Cotação de {_fmt_moeda(av['cotacao'])} frente a um Preço-Teto "
            f"Projetivo de {_fmt_moeda(av['preco_teto_projetivo'])}."
        ),
        "secoes": secoes,
        "ativos": [ativo["ticker"]],
        "dados": {"ativo": ativo, "valuation": av, "risco": risco, "premio_lci": premio},
    }


def relatorio_tema_selic(subindo: bool = True) -> dict[str, Any]:
    tema = "selic_alta" if subindo else "selic_queda"
    regra = news_service.MATRIZ_IMPACTO[tema]
    ativos = {a["ticker"]: a for a in market_service.listar_ativos()["ativos"]}
    macro = market_service.indicadores_macro()

    def linha(t: str) -> str:
        a = ativos.get(t, {})
        return f"{t} — {a.get('nome', '')} ({a.get('setor', '')})"

    explic_benef = (
        "Bancos e seguradoras aplicam o caixa (float) a juros maiores; FIIs de papel recebem CRIs atrelados ao CDI."
        if subindo else
        "Juros menores barateiam o crédito, estimulam o consumo e valorizam imóveis e empresas de crescimento."
    )
    return {
        "titulo": f"Quem ganha e quem perde com a {'alta' if subindo else 'queda'} da Selic",
        "resumo": (
            f"Selic atual: {_fmt_pct(macro['selic_anual'], 2)} a.a.; CDI: {_fmt_pct(macro['cdi_anual'], 2)}; "
            f"juro real aproximado: {_fmt_pct(macro['juro_real'], 2)}. {explic_benef}"
        ),
        "secoes": [
            {"titulo": "Beneficiados", "itens": [linha(t) for t in regra["beneficiados"]]},
            {"titulo": "Prejudicados", "itens": [linha(t) for t in regra["prejudicados"]]},
            {"titulo": "Renda fixa", "itens": [regra["renda_fixa"],
             "LCI e LCA são isentas de IR: compare sempre pela taxa CDB equivalente (gross-up)."]},
        ],
        "ativos": regra["beneficiados"] + regra["prejudicados"],
        "dados": {"macro": macro, "regra": regra},
    }


def relatorio_comparacao_lci(pergunta: str, tickers: list[str]) -> dict[str, Any]:
    """Compara uma LCI/LCA (% do CDI citado na pergunta) com os ativos citados."""
    m = re.search(r"(\d{2,3}(?:[.,]\d+)?)\s*%", pergunta)
    taxa_lci = float(m.group(1).replace(",", ".")) if m else 92.0
    macro = market_service.indicadores_macro()
    cdi = macro["cdi_anual"] / 100
    rend_lci = cdi * taxa_lci
    itens_cmp: list[str] = []
    dados: list[dict[str, Any]] = []
    for t in tickers or ["HGLG11"]:
        ativo = market_service.obter_ativo(t)
        if not ativo:
            continue
        av = valuation.avaliar_ativo(ativo)
        premio = fixed_income.premio_de_risco(av["dy_projetado"] or 0, taxa_lci, cdi)
        dados.append({"ticker": t, "premio": premio})
        itens_cmp.append(
            f"{t}: DY projetado de {_fmt_pct(av['dy_projetado'], 2)} (isento) vs. LCI {taxa_lci:.0f}% do CDI = "
            f"{_fmt_pct(rend_lci, 2)} a.a. (isenta). {premio['leitura']} (diferença de {_fmt_num(premio['premio_pp'])} p.p.)"
        )
    equiv = fixed_income.taxa_cdb_equivalente(taxa_lci, 721)
    return {
        "titulo": f"LCI {taxa_lci:.0f}% do CDI × renda variável",
        "resumo": (
            f"Com CDI de {_fmt_pct(macro['cdi_anual'], 2)}, uma LCI a {taxa_lci:.0f}% do CDI rende cerca de "
            f"{_fmt_pct(rend_lci, 2)} ao ano, sem IR — equivale a um CDB de {_fmt_pct(equiv)} do CDI em prazos acima de 2 anos."
        ),
        "secoes": [
            {"titulo": "Comparação de rendimento", "itens": itens_cmp},
            {"titulo": "Diferenças de risco", "itens": [
                "LCI/LCA: renda fixa, coberta pelo FGC até R$ 250 mil por instituição; liquidez só no vencimento (em geral).",
                "FIIs e ações: renda variável; cotas oscilam diariamente, mas há liquidez na bolsa e potencial de valorização.",
                "Dividendos de FII não são garantidos: dependem de aluguéis, vacância e inadimplência.",
            ]},
        ],
        "ativos": [d["ticker"] for d in dados],
        "dados": {"taxa_lci": taxa_lci, "rendimento_lci": rend_lci, "comparacoes": dados},
    }


def relatorio_panorama() -> dict[str, Any]:
    """Visão geral: macro + ranking do Score Alpha."""
    macro = market_service.indicadores_macro()
    sent = news_service.sentimento_por_ativo()
    ranking = sorted(
        (valuation.avaliar_ativo(a, sentimento_noticias=sent.get(a["ticker"], 0.0)) | {"nome": a["nome"]}
         for a in market_service.listar_ativos()["ativos"]),
        key=lambda x: x["score"]["total"], reverse=True,
    )
    return {
        "titulo": "Panorama do mercado e ranking Score Alpha",
        "resumo": (
            f"Selic {_fmt_pct(macro['selic_anual'], 2)}, IPCA 12m {_fmt_pct(macro['ipca_12m'], 2)}, "
            f"juro real {_fmt_pct(macro['juro_real'], 2)}. Com juro real alto, a renda fixa isenta (LCI/LCA) "
            "é uma concorrente forte da bolsa: exija margem de segurança."
        ),
        "secoes": [
            {"titulo": "Top 5 Score Alpha", "itens": [
                f"{r['ticker']} ({r['nome']}): {r['score']['total']:.0f}/100 — margem projetiva {_fmt_pct(r['margem_projetiva'])}"
                for r in ranking[:5]]},
            {"titulo": "Menores notas", "itens": [
                f"{r['ticker']} ({r['nome']}): {r['score']['total']:.0f}/100" for r in ranking[-3:]]},
            {"titulo": "Dica", "itens": [
                "Pergunte, por exemplo: 'Avalie o histórico e o risco de PETR4' ou 'Compare LCI 92% do CDI com o FII HGLG11'."]},
        ],
        "ativos": [r["ticker"] for r in ranking[:5]],
        "dados": {"macro": macro, "top5": [{"ticker": r["ticker"], "score": r["score"]["total"]} for r in ranking[:5]]},
    }


def motor_de_regras(pergunta: str, ticker: str | None = None) -> dict[str, Any]:
    """Roteia a pergunta para o relatório adequado (intenção por palavras-chave)."""
    p = news_service.normalizar(pergunta or "")
    tickers = _tickers_na_pergunta(pergunta or "")
    if ticker and ticker.upper() not in tickers:
        tickers.insert(0, ticker.upper())

    if ("lci" in p or "lca" in p) and ("compar" in p or tickers):
        return relatorio_comparacao_lci(pergunta, tickers)
    if "selic" in p or "juros" in p:
        queda = any(w in p for w in ("queda", "corte", "cair", "baixa", "reduc"))
        if not tickers or "ganha" in p or "quais" in p:
            return relatorio_tema_selic(subindo=not queda)
    if tickers:
        return relatorio_ativo(tickers[0])
    return relatorio_panorama()


# ---------------------------------------------------------------------------
# Modo LLM — vários provedores, com os gratuitos primeiro
# ---------------------------------------------------------------------------
# Provedores gratuitos (cada um exige a própria chave no .env):
#   gemini     GEMINI_API_KEY      Google AI Studio, plano gratuito
#   groq       GROQ_API_KEY        plano gratuito, muito rápido
#   openrouter OPENROUTER_API_KEY  modelos com sufixo ":free"
# Pagos (opcionais): deepseek (DEEPSEEK_API_KEY) e anthropic (ANTHROPIC_API_KEY).
#
# Escolha (variável AI_PROVIDER): "auto" tenta, na ordem acima, todo provedor que
# tem chave e passa para o próximo se um falhar ou estourar o limite gratuito;
# ou force um nome específico.

ORDEM_PROVEDORES = ["gemini", "groq", "openrouter", "deepseek", "anthropic"]
CHAVES_PROVEDOR = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}
# Endpoints no formato OpenAI: (url, modelo padrão, variável para trocar o modelo)
ENDPOINTS_OPENAI = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "openai/gpt-oss-120b", "GROQ_MODEL"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "google/gemma-4-31b-it:free", "OPENROUTER_MODEL"),
    "deepseek": ("https://api.deepseek.com/chat/completions", "deepseek-chat", "DEEPSEEK_MODEL"),
}
# Modelos de reserva (limites independentes do modelo principal).
MODELOS_RESERVA = {"groq": ["openai/gpt-oss-20b"]}
URL_GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
MODELO_GEMINI = "gemini-2.5-flash"


def provedores_ativos() -> list[str]:
    """Provedores a tentar, em ordem: os que têm chave (ou só o forçado por AI_PROVIDER)."""
    escolhido = os.getenv("AI_PROVIDER", "auto").strip().lower()
    com_chave = [p for p in ORDEM_PROVEDORES if os.getenv(CHAVES_PROVEDOR[p], "").strip()]
    if escolhido in CHAVES_PROVEDOR:
        return [escolhido] if escolhido in com_chave else []
    return com_chave


def provedor_ia() -> str | None:
    ativos = provedores_ativos()
    return ativos[0] if ativos else None


def llm_disponivel() -> bool:
    return bool(provedores_ativos())


def _mensagem_usuario(pergunta: str, base: dict[str, Any]) -> str:
    """Pergunta + números já calculados pelo Python: o LLM só interpreta, não calcula."""
    dados = {
        "titulo": base["titulo"],
        "resumo_calculado": base["resumo"],
        "secoes_calculadas": base["secoes"],
        "macro": market_service.indicadores_macro(),
    }
    return "PERGUNTA: " + pergunta + "\n\nDADOS:\n" + json.dumps(dados, ensure_ascii=False, default=str)


def _perguntar_openai_compat(provedor: str, pergunta: str, base: dict[str, Any]) -> str:
    """Groq, OpenRouter e DeepSeek usam o mesmo formato de chat; chamada com ``requests``."""
    import requests

    url, modelo_padrao, var_modelo = ENDPOINTS_OPENAI[provedor]
    principal = os.getenv(var_modelo, "").strip() or modelo_padrao
    # Cada modelo tem o seu próprio limite: se um estourar, o reserva ainda responde.
    modelos = [principal] + [m for m in MODELOS_RESERVA.get(provedor, []) if m != principal]
    mensagem = _mensagem_usuario(pergunta, base)
    ultimo_erro: Exception = RuntimeError("nenhum modelo tentado")

    for modelo in modelos:
        corpo: dict[str, Any] = {
            "model": modelo,
            "max_tokens": 1200,  # o limite por minuto conta o máximo pedido, não só o usado
            "temperature": 0.3,  # baixa: fidelidade aos números, não criatividade
            "messages": [
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": mensagem},
            ],
        }
        if provedor == "groq" and modelo.startswith("openai/gpt-oss"):
            corpo["reasoning_effort"] = "low"  # menos "raciocínio" interno = menos tokens e mais rapidez

        for tentativa in range(2):
            resp = requests.post(
                url,
                headers={"Authorization": f"Bearer {os.environ[CHAVES_PROVEDOR[provedor]].strip()}"},
                json=corpo,
                timeout=60,
            )
            if resp.status_code == 429:
                # Limite por minuto: o servidor diz quanto esperar. Esperas curtas valem a pena.
                espera = _segundos_de_espera(resp)
                ultimo_erro = requests.HTTPError("429 limite de uso", response=resp)
                if tentativa == 0 and espera <= 12:
                    time.sleep(espera + 0.5)
                    continue
                break  # espera longa (limite diário): passa ao modelo reserva
            try:
                resp.raise_for_status()
                texto = (resp.json()["choices"][0]["message"].get("content") or "").strip()
                if not texto:
                    raise RuntimeError("resposta vazia")
                return texto
            except Exception as erro:  # noqa: BLE001
                ultimo_erro = erro
                break
    raise ultimo_erro


def _segundos_de_espera(resp: Any) -> float:
    """Lê o tempo de espera de uma resposta 429 (cabeçalho Retry-After; padrão 10 s)."""
    try:
        return float(resp.headers.get("retry-after", 10))
    except (TypeError, ValueError):
        return 10.0


def _perguntar_ao_gemini(pergunta: str, base: dict[str, Any]) -> str:
    import requests

    modelo = os.getenv("GEMINI_MODEL", "").strip() or MODELO_GEMINI
    resp = requests.post(
        URL_GEMINI.format(modelo=modelo),
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"].strip()},  # chave no header, nunca na URL
        json={
            "systemInstruction": {"parts": [{"text": PROMPT_SISTEMA}]},
            "contents": [{"role": "user", "parts": [{"text": _mensagem_usuario(pergunta, base)}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000},
        },
        timeout=60,
    )
    resp.raise_for_status()
    partes = resp.json()["candidates"][0]["content"]["parts"]
    texto = "".join(p.get("text", "") for p in partes if not p.get("thought")).strip()
    if not texto:
        raise RuntimeError("resposta vazia")
    return texto


def _perguntar_ao_claude(pergunta: str, base: dict[str, Any]) -> str:
    import anthropic

    cliente = anthropic.Anthropic(timeout=60.0)
    resposta = cliente.beta.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", MODELO_PADRAO),
        max_tokens=4000,
        system=PROMPT_SISTEMA,
        output_config={"effort": "medium"},
        # Se o modelo principal recusar, a API tenta automaticamente outro modelo.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": _mensagem_usuario(pergunta, base)}],
    )
    if resposta.stop_reason == "refusal":
        raise RuntimeError("o modelo recusou a solicitação")
    texto = "".join(b.text for b in resposta.content if b.type == "text").strip()
    if not texto:
        raise RuntimeError("resposta vazia do modelo")
    return texto


def _perguntar(provedor: str, pergunta: str, base: dict[str, Any]) -> str:
    """Chama o provedor, guardando a resposta por 10 min para não gastar a cota gratuita à toa."""
    chave = "ia:" + provedor + ":" + hashlib.md5(_mensagem_usuario(pergunta, base).encode()).hexdigest()

    def _chamar() -> str:
        if provedor == "gemini":
            return _perguntar_ao_gemini(pergunta, base)
        if provedor == "anthropic":
            return _perguntar_ao_claude(pergunta, base)
        return _perguntar_openai_compat(provedor, pergunta, base)

    return market_service._cache.obter_ou_calcular(chave, 600, _chamar)


def analisar(pergunta: str, ticker: str | None = None, usar_llm: bool = True) -> dict[str, Any]:
    """
    Ponto de entrada usado pela rota ``POST /api/ai/analyze``.

    Sempre calcula a resposta pelo motor de regras; se houver provedor de IA
    configurado, ele reescreve a análise em linguagem natural. Se o primeiro
    falhar (limite gratuito, erro de rede), tenta o seguinte.
    """
    pergunta = (pergunta or "").strip() or (f"Avalie o histórico e o risco de {ticker}" if ticker else "Panorama do mercado")
    base = motor_de_regras(pergunta, ticker)
    base.pop("dados", None)  # dados brutos ficam internos (não poluem a resposta)
    resultado = {"pergunta": pergunta, "modo": "regras", "provedor": None, "texto_llm": None, "aviso": AVISO_LEGAL, **base}

    if usar_llm:
        for provedor in provedores_ativos():
            try:
                resultado["texto_llm"] = _perguntar(provedor, pergunta, base)
                resultado["modo"] = "llm"
                resultado["provedor"] = provedor
                resultado.pop("aviso_llm", None)
                break
            except Exception as erro:  # noqa: BLE001 — nunca quebrar a resposta
                # Só o tipo do erro: a mensagem de requests inclui a URL.
                logger.warning("%s indisponível (%s), tentando o próximo.", provedor, type(erro).__name__)
                resultado["aviso_llm"] = "A IA generativa não respondeu; exibindo a análise do motor de regras em Python."
    return resultado
