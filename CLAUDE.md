# Especificação do Projeto: AlphaRadar B3 (Python FastAPI + Next.js)

## Visão Geral e Originalidade
Plataforma autoral e open-source de acompanhamento de investimentos brasileiros (Ações da B3, Fundos Imobiliários - FIIs, LCI, LCA, CDB e Tesouro Direto) com atualização em tempo real, radar de notícias com impacto cruzado e analista de Inteligência Artificial.
- Código, interface visual, nomes de módulos e textos 100% originais.
- Toda a inteligência financeira, coleta de dados e regras de negócio devem ser escritas em **Python** na pasta `/backend` usando código limpo, tipado e amplamente comentado em português para fins de estudo de Engenharia de Software.

## Arquitetura em Produção
1. **Backend em Python (`/backend`)**:
   - Framework: `FastAPI` + `uvicorn` (porta `8000`)
   - Manipulação de dados: `pandas` e `numpy`
   - Dados de mercado: `yfinance` (tickers da B3 com sufixo `.SA`), API pública `brapi.dev` e API SGS do Banco Central do Brasil (`api.bcb.gov.br` / `python-bcb`) para Taxa Selic, CDI e IPCA.
   - Resiliência Obrigatória: Crie `backend/data/fallback_b3.json` com dados realistas de 16 ativos da B3 (BBAS3, PETR4, VALE3, ITUB4, WEGE3, TAEE11, BBSE3, EGIE3, PRIO3, SUZB3, RENT3, RADL3, HGLG11, MXRF11, KNRI11, XPML11) e 12 notícias financeiras. Se `yfinance` ou a internet falharem, o Python deve retornar os dados do fallback sem nunca gerar erro 500.
2. **Frontend Web (`/frontend`)**:
   - Next.js (App Router) + TypeScript + Tailwind CSS + `lucide-react` + `recharts`
   - Consome a API Python em `http://localhost:8000/api/...`

## Motores Matemáticos em Python (`backend/engine/`)
- `valuation.py`:
  1. `preco_justo_graham(lpa, vpa)` -> `sqrt(22.5 * lpa * vpa)`
  2. `preco_teto_bazin_historico(dpa_12m, yield_min=0.06)` -> `dpa_12m / yield_min`
  3. `preco_teto_projetivo(lpa, crescimento_g, payout_pct, yield_desejado)` -> `(lpa * (1 + crescimento_g) * (payout_pct / 100)) / yield_desejado`
  4. `calcular_score_alpha(ativo)` -> Nota de 0 a 100 dividida em 5 pilares de 20 pontos (Margem Preço-Teto, Dividend Yield, Rentabilidade ROE, Endividamento Dívida/EBITDA e Sentimento de Notícias).
- `fixed_income.py`:
  1. Cálculo de rentabilidade líquida de LCI e LCA (isentas de Imposto de Renda) vs CDB (alíquota regressiva de IR: 22.5%, 20%, 17.5% e 15%).
  2. Cálculo de Taxa CDB Equivalente (`taxa_lci / (1 - aliquota_ir)`) e curva de evolução patrimonial mensal em juros compostos.
- `ai_analyst.py`:
  1. Analisa o histórico, os múltiplos, o risco e as notícias do ativo usando LLM (Anthropic/Gemini API se configurada no `.env`, ou motor analítico em Python baseado em regras fundamentais caso esteja sem chave de API).

