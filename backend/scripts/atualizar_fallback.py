"""
atualizar_fallback.py — Atualiza o catálogo de reserva (data/fallback_b3.json) com dados reais do Yahoo
=======================================================================================================

Uso (dentro da pasta backend, com o ambiente virtual ativo):

    python scripts/atualizar_fallback.py

O que faz:
    1. Adiciona ao catálogo os ativos da lista NOVOS que ainda não existem (se o Yahoo tiver dados).
    2. Atualiza cotação, variação e fundamentos (LPA, VPA, dividendos, ROE, P/L, P/VP...) de todos.
    3. Reescreve o JSON mantendo o formato legível (um ativo por linha).

Rode de vez em quando (a cada balanço trimestral) para o modo offline continuar fiel à realidade.
Para incluir uma empresa nova, acrescente uma linha em NOVOS e rode o script.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services import b3_service, fundamentals_service  # noqa: E402

CAMINHO = Path(__file__).resolve().parent.parent / "data" / "fallback_b3.json"

# (ticker, nome, tipo, setor) — FIIs só entram se o Yahoo informar o valor patrimonial (VPA).
NOVOS = [
    ("ITSA4", "Itaúsa", "acao", "Holding financeira"), ("BBDC4", "Bradesco", "acao", "Bancos"),
    ("ABEV3", "Ambev", "acao", "Bebidas"), ("B3SA3", "B3", "acao", "Bolsa e serviços financeiros"),
    ("SANB11", "Santander Brasil", "acao", "Bancos"), ("CMIG4", "Cemig", "acao", "Energia Elétrica"),
    ("VIVT3", "Vivo (Telefônica Brasil)", "acao", "Telecomunicações"), ("KLBN11", "Klabin", "acao", "Papel e Celulose"),
    ("GGBR4", "Gerdau", "acao", "Siderurgia"), ("EQTL3", "Equatorial", "acao", "Energia Elétrica"),
    ("LREN3", "Lojas Renner", "acao", "Varejo"), ("MGLU3", "Magazine Luiza", "acao", "Varejo"),
    ("SAPR11", "Sanepar", "acao", "Saneamento"), ("CXSE3", "Caixa Seguridade", "acao", "Seguros"),
    ("TIMS3", "TIM", "acao", "Telecomunicações"), ("CSAN3", "Cosan", "acao", "Energia e Logística"),
    ("CPFE3", "CPFL Energia", "acao", "Energia Elétrica"), ("ALUP11", "Alupar", "acao", "Energia Elétrica"),
    ("BTLG11", "BTG Pactual Logística FII", "fii", "FII Logística"),
    ("KNCR11", "Kinea Rendimentos Imobiliários FII", "fii", "FII Papel (CRI)"),
]


def main() -> None:
    dados = json.loads(CAMINHO.read_text(encoding="utf-8"))
    existentes = {a["ticker"] for a in dados["ativos"]}
    for ticker, nome, tipo, setor in NOVOS:
        if ticker not in existentes:
            dados["ativos"].append({
                "ticker": ticker, "nome": nome, "tipo": tipo, "mercado": "B3", "moeda": "BRL", "setor": setor,
                "cotacao": 0.0, "variacao_dia": 0.0, "lpa": 0.0, "vpa": 0.0, "dpa_12m": 0.0, "payout_medio": 0,
                "crescimento_lucro": 0.0, "roe": 0.0, "divida_liquida_ebitda": None, "pl": None, "pvp": None, "beta": 1.0,
            })

    ativos = dados["ativos"]
    from services import market_service  # noqa: E402

    cot = b3_service.cotacoes_yfinance([a["ticker"] for a in ativos], {a["ticker"]: market_service.simbolo_yahoo(a) for a in ativos})
    fund = fundamentals_service.baixar_fundamentos(ativos, timeout=120)
    sem_dados = []
    for a in list(ativos):
        c = cot.get(a["ticker"])
        if not c:
            sem_dados.append(a["ticker"])
            continue
        a.update(c)
        campos = fund.get(a["ticker"], {})
        if a["tipo"] == "fii" and not (campos.get("vpa") or a.get("vpa")):
            sem_dados.append(a["ticker"])  # FII sem valor patrimonial: não inventamos
            continue
        fundamentals_service.aplicar_fundamentos(a, campos)
        a.pop("fonte_fundamentos", None)
    novos_ruins = [t for t in sem_dados if t in {n[0] for n in NOVOS} and t not in existentes]
    dados["ativos"] = [a for a in ativos if a["ticker"] not in novos_ruins]

    linhas = ["{", f'  "_sobre": {json.dumps(dados["_sobre"], ensure_ascii=False)},',
              f'  "atualizado_em": "{__import__("datetime").date.today().isoformat()}",',
              f'  "macro": {json.dumps(dados["macro"], ensure_ascii=False)},', '  "ativos": [',
              ",\n".join("    " + json.dumps(a, ensure_ascii=False) for a in dados["ativos"]), "  ],", '  "noticias": [',
              ",\n".join("    " + json.dumps(n, ensure_ascii=False) for n in dados["noticias"]), "  ]", "}"]
    CAMINHO.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    tickers_ts = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "tickers.ts"
    nomes = [a["ticker"] for a in dados["ativos"]]
    corpo = ",
".join("  " + ", ".join(f'"{t}"' for t in nomes[i:i + 8]) for i in range(0, len(nomes), 8))
    tickers_ts.write_text(
        "// Gerado por backend/scripts/atualizar_fallback.py a partir de backend/data/fallback_b3.json. Não edite à mão.
"
        f"export const TICKERS = [
{corpo},
] as const;
", encoding="utf-8")
    print(f"{len(dados['ativos'])} ativos salvos. Sem dados no Yahoo (ignorados ou mantidos): {sem_dados or 'nenhum'}")


if __name__ == "__main__":
    main()
