"""Testes da API em modo offline (usam só o fallback: sem internet e sem chaves)."""

import os

os.environ["ALPHARADAR_OFFLINE"] = "1"
for chave in ("GROQ_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "ANTHROPIC_API_KEY", "NEWS_RSS_URLS"):
    os.environ[chave] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from services import global_service  # noqa: E402


@pytest.fixture(scope="module")
def cliente():
    with TestClient(main.app) as c:
        yield c


@pytest.mark.parametrize("rota", ["/api/health", "/api/overview", "/api/assets", "/api/assets/PETR4", "/api/assets/NVDA",
                                  "/api/news-radar", "/api/mercado", "/api/macro"])
def test_rotas_respondem_200_offline(cliente, rota):
    assert cliente.get(rota).status_code == 200


def test_catalogo_tem_b3_e_eua_e_ativo_inexistente_da_404(cliente):
    j = cliente.get("/api/assets").json()
    assert j["total"] >= 40
    assert {a["mercado"] for a in j["ativos"]} == {"B3", "EUA"}
    assert cliente.get("/api/assets/XXXX3").status_code == 404
    assert cliente.get("/api/assets?mercado=EUA").json()["total"] == 10


def test_scores_validos_para_todos_os_ativos(cliente):
    for a in cliente.get("/api/assets").json()["ativos"]:
        assert 0 <= a["score"]["total"] <= 100, a["ticker"]


def test_simulador_valida_entrada(cliente):
    assert cliente.post("/api/simulate/valuation", json={"yield_desejado": 0.5}).status_code == 422
    assert cliente.post("/api/simulate/fixed-income", json={"meses": 0}).status_code == 422
    r = cliente.post("/api/simulate/valuation", json={"ticker": "PETR4", "yield_desejado": 0.08, "crescimento_g": 0.05, "payout_pct": 60})
    assert r.status_code == 200 and r.json()["resultados"][0]["premissas"]["yield_desejado"] == 0.08


def test_analista_funciona_sem_chave_e_entende_nomes_de_empresas(cliente):
    r = cliente.post("/api/ai/analyze", json={"pergunta": "Avalie o risco da Nvidia"}).json()
    assert r["modo"] == "regras" and "NVDA" in r["titulo"]


def test_limite_de_uso_da_ia(cliente, monkeypatch):
    monkeypatch.setattr(main, "LIMITE_IA_POR_MINUTO", 2)
    main._acessos_ia.clear(); main._acessos_globais.clear()
    codigos = [cliente.post("/api/ai/analyze", json={"pergunta": "panorama"}).status_code for _ in range(4)]
    assert codigos == [200, 200, 429, 429]


def test_mercado_offline_traz_grupos_e_risco(cliente):
    j = cliente.get("/api/mercado").json()
    assert j["fonte"] == "fallback" and {g["id"] for g in j["grupos"]} >= {"bolsas", "moedas", "commodities", "juros_eua"}
    assert j["risco"]["rotulo"] in {"Apetite alto", "Neutro", "Apetite baixo"}


def test_termometro_de_risco_reage_ao_vix():
    calmo = {"volatilidade": [{"simbolo": "^VIX", "valor": 13, "variacao": 0}], "bolsas": [{"simbolo": "^GSPC", "valor": 1, "variacao": 0.8}]}
    medo = {"volatilidade": [{"simbolo": "^VIX", "valor": 30, "variacao": 5}], "bolsas": [{"simbolo": "^GSPC", "valor": 1, "variacao": -1.2}]}
    assert global_service.termometro_risco(calmo)["rotulo"] == "Apetite alto"
    assert global_service.termometro_risco(medo)["rotulo"] == "Apetite baixo"


def test_traducao_de_eventos_da_agenda():
    assert "payroll" in global_service._traduzir("Non-Farm Employment Change").lower()
    assert global_service._traduzir("Evento Desconhecido XYZ") == "Evento Desconhecido XYZ"


# ---------------------------------------------------------------- segurança
def test_cabecalhos_de_seguranca_na_api(cliente):
    h = cliente.get("/api/health").headers
    assert h["x-content-type-options"] == "nosniff"
    assert h["x-frame-options"] == "DENY"
    assert "frame-ancestors 'none'" in h["content-security-policy"]


def test_cors_so_libera_o_proprio_site(cliente):
    def origem(o):
        r = cliente.options("/api/overview", headers={"Origin": o, "Access-Control-Request-Method": "GET"})
        return r.headers.get("access-control-allow-origin")

    assert origem("http://localhost:3000") == "http://localhost:3000"
    assert origem("https://alpharadar-b3.up.railway.app") == "https://alpharadar-b3.up.railway.app"
    assert origem("https://site-malicioso.com") is None
    assert origem("https://qualquer-outro.up.railway.app") is None  # nem domínios da Railway de terceiros


def test_ip_do_cliente_so_confia_nos_cabecalhos_vindos_de_proxy_interno(cliente):
    class Req:
        def __init__(self, host, **cab):
            self.headers = {k.replace("_", "-"): v for k, v in cab.items()}
            self.client = type("C", (), {"host": host})()

    forjado = "9.9.9.9, 8.8.8.8, 203.0.113.7"
    # Railway: X-Real-IP é do visitante real; o último do X-Forwarded-For é o proxy de borda (varia)
    assert main._ip_do_cliente(Req("100.64.0.11", x_real_ip="191.37.37.101", x_forwarded_for="191.37.37.101, 46.151.194.129")) == "191.37.37.101"
    assert main._ip_do_cliente(Req("100.64.0.11", x_forwarded_for=forjado)) == "203.0.113.7"  # proxy que só acrescenta: vale o último
    assert main._ip_do_cliente(Req("127.0.0.1", x_forwarded_for=forjado)) == "203.0.113.7"  # local
    # visitante direto da internet (IP público): cabeçalhos ignorados
    assert main._ip_do_cliente(Req("93.184.216.34", x_forwarded_for=forjado, x_real_ip="7.7.7.7")) == "93.184.216.34"
    assert main._ip_do_cliente(Req("100.64.0.11")) == "100.64.0.11"


def test_ip_falso_no_cabecalho_nao_burla_o_limite_por_ip(monkeypatch):
    monkeypatch.setattr(main, "LIMITE_IA_POR_MINUTO", 3)
    main._acessos_ia.clear(); main._acessos_globais.clear()
    # cliente que se conecta como o proxy interno da Railway: o último X-Forwarded-For é o visitante real
    with TestClient(main.app, client=("100.64.0.11", 50000)) as proxy:
        codigos = [
            proxy.post(
                "/api/ai/analyze",
                json={"pergunta": "panorama"},
                headers={"X-Real-IP": "191.37.37.101", "X-Forwarded-For": f"191.37.37.101, 46.151.194.{i}"},  # borda varia
            ).status_code
            for i in range(6)
        ]
    assert codigos == [200, 200, 200, 429, 429, 429]


def test_visitante_direto_nao_forja_ip_pelo_cabecalho(monkeypatch):
    monkeypatch.setattr(main, "LIMITE_IA_POR_MINUTO", 3)
    main._acessos_ia.clear(); main._acessos_globais.clear()
    with TestClient(main.app, client=("93.184.216.34", 50000)) as direto:  # IP público, sem proxy
        codigos = [
            direto.post("/api/ai/analyze", json={"pergunta": "panorama"}, headers={"X-Forwarded-For": f"1.1.1.{i}"}).status_code
            for i in range(5)
        ]
    assert codigos == [200, 200, 200, 429, 429]  # mudar o cabeçalho a cada pedido não adianta


@pytest.mark.parametrize("link,esperado", [
    ("https://exemplo.com/noticia", "https://exemplo.com/noticia"),
    ("http://exemplo.com/a?b=1", "http://exemplo.com/a?b=1"),
    ("javascript:alert(document.cookie)", None),
    ("JaVaScRiPt:alert(1)", None),
    ("data:text/html,<script>alert(1)</script>", None),
    ("//exemplo.com/sem-esquema", None),
    ("", None),
    (None, None),
])
def test_links_de_noticias_so_aceitam_http(link, esperado):
    from services import news_service
    assert news_service._link_seguro(link) == esperado
