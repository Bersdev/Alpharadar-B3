"""Testes dos motores matemáticos (sem internet). Rode com:  pytest  (dentro da pasta backend)."""

import math

import pytest

from engine import fixed_income as rf
from engine import valuation as v
from services.fundamentals_service import aplicar_fundamentos, extrair_fundamentos


# ---------------------------------------------------------------- valuation
def test_graham_formula_classica():
    assert v.preco_justo_graham(2.0, 10.0) == pytest.approx(math.sqrt(22.5 * 20))


@pytest.mark.parametrize("lpa,vpa", [(-1, 10), (2, -5), (0, 10), (None, 10)])
def test_graham_nao_se_aplica_a_prejuizo(lpa, vpa):
    assert v.preco_justo_graham(lpa, vpa) is None


def test_bazin_e_projetivo():
    assert v.preco_teto_bazin_historico(1.2, 0.06) == pytest.approx(20.0)
    # LPA 4, crescimento 5%, payout 50%, yield 6%: (4 * 1,05 * 0,5) / 0,06 = 35
    assert v.preco_teto_projetivo(4.0, 0.05, 50, 0.06) == pytest.approx(35.0)
    assert v.preco_teto_projetivo(4.0, 0.05, 50, 0) is None
    assert v.preco_teto_projetivo(-1.0, 0.05, 50, 0.06) is None  # prejuízo: sem dividendo projetado


def test_margem_de_seguranca():
    assert v.margem_seguranca(30.0, 25.0) == pytest.approx(20.0)
    assert v.margem_seguranca(20.0, 25.0) == pytest.approx(-20.0)
    assert v.margem_seguranca(None, 25.0) is None


def test_score_alpha_fica_entre_0_e_100_e_tem_5_pilares():
    ativo = {"cotacao": 20, "lpa": 3, "vpa": 15, "payout_medio": 60, "crescimento_lucro": 0.05, "roe": 15, "divida_liquida_ebitda": 1.0}
    s = v.calcular_score_alpha(ativo, sentimento_noticias=0.3)
    assert len(s.pilares) == 5
    assert 0 <= s.total <= 100
    assert all(0 <= p.pontos <= 20 for p in s.pilares)


def test_score_sem_indicador_de_divida_recebe_nota_neutra():
    ativo = {"cotacao": 20, "lpa": 3, "vpa": 15, "payout_medio": 60, "crescimento_lucro": 0, "roe": 15, "divida_liquida_ebitda": None}
    pilar = v.calcular_score_alpha(ativo).pilares[3]
    assert pilar.pontos == pytest.approx(14.0)  # 70% de 20


def test_fii_usa_yield_de_referencia_maior_e_nao_tem_graham():
    fii = {"ticker": "XXXX11", "tipo": "fii", "cotacao": 100, "lpa": 10, "vpa": 100, "dpa_12m": 9.5, "payout_medio": 95, "crescimento_lucro": 0}
    r = v.avaliar_ativo(fii)
    assert r["premissas"]["yield_desejado"] == pytest.approx(0.08)
    assert r["preco_justo_graham"] is None


# ---------------------------------------------------------------- renda fixa
@pytest.mark.parametrize("dias,esperado", [(100, 0.225), (180, 0.225), (181, 0.20), (360, 0.20), (500, 0.175), (720, 0.175), (721, 0.15)])
def test_tabela_regressiva_de_ir(dias, esperado):
    assert rf.aliquota_ir(dias) == esperado


def test_gross_up_lci_para_cdb():
    # LCI a 92% do CDI por mais de 2 anos (IR de 15%): 92 / 0,85
    assert rf.taxa_cdb_equivalente(92, 800) == pytest.approx(92 / 0.85)
    assert rf.taxa_isenta_equivalente(rf.taxa_cdb_equivalente(92, 800), 800) == pytest.approx(92)


def test_simulacao_lci_vence_cdb_de_mesma_taxa_e_curva_tem_tamanho_certo():
    r = rf.simular_renda_fixa(rf.ParametrosSimulacao(meses=24, taxa_lci_pct_cdi=100, taxa_cdb_pct_cdi=100, aporte_mensal=0))
    assert len(r["curva_mensal"]) == 25
    por_nome = {p["produto"]: p["valor_final_liquido"] for p in r["produtos"]}
    assert por_nome["LCI"] > por_nome["CDB"]  # a isenção de IR é a única diferença
    assert r["economia_ir_lci"] > 0


def test_premio_de_risco_desconta_ir_dos_dividendos_dos_eua():
    br = rf.premio_de_risco(10.0, 92, 0.1365, "B3")
    eua = rf.premio_de_risco(10.0, 92, 0.1365, "EUA")
    assert eua["premio_pp"] == pytest.approx(br["premio_pp"] - 3.0)  # 30% de 10 p.p.


# ---------------------------------------------------------------- fundamentos
def test_extrair_fundamentos_de_acao():
    info = {"trailingEps": 2.0, "forwardEps": 5.0, "bookValue": 20.0, "trailingAnnualDividendRate": 1.0,
            "payoutRatio": 0.5, "returnOnEquity": 0.12, "totalDebt": 300.0, "totalCash": 100.0, "ebitda": 100.0}
    f = extrair_fundamentos(info, "acao", "Varejo")
    assert f["lpa"] == 2.0 and f["vpa"] == 20.0 and f["dpa_12m"] == 1.0
    assert f["roe"] == 12.0 and f["payout_medio"] == 50
    assert f["crescimento_lucro"] == 0.20  # 150% de crescimento projetado é limitado a 20%
    assert f["divida_liquida_ebitda"] == 2.0


def test_banco_nao_recebe_divida_ebitda_e_dados_invalidos_sao_ignorados():
    f = extrair_fundamentos({"trailingEps": float("nan"), "totalDebt": 5, "totalCash": 1, "ebitda": 2, "bookValue": -3}, "acao", "Bancos")
    assert "lpa" not in f and "vpa" not in f and "divida_liquida_ebitda" not in f


def test_aplicar_fundamentos_recalcula_pl_pvp_e_fii():
    acao = {"tipo": "acao", "cotacao": 20.0}
    aplicar_fundamentos(acao, {"lpa": 2.0, "vpa": 10.0, "dpa_12m": 1.0})
    assert acao["pl"] == 10.0 and acao["pvp"] == 2.0 and acao["payout_medio"] == 50
    fii = {"tipo": "fii", "cotacao": 100.0}
    aplicar_fundamentos(fii, {"dpa_12m": 9.5, "vpa": 100.0})
    assert fii["lpa"] == pytest.approx(10.0) and fii["roe"] == pytest.approx(9.5) and fii["payout_medio"] == 95
