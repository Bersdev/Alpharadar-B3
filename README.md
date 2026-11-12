# AlphaRadar B3

**Demonstração ao vivo: https://alpharadar-b3.up.railway.app**

Plataforma open-source de análise de investimentos — ações da B3, fundos imobiliários (FIIs), ações dos EUA (NVIDIA, Microsoft, Apple e outras), LCI, LCA, CDB e Tesouro Selic — com **motor financeiro escrito em Python** e dashboard web em Next.js.

O sistema transforma dados públicos de mercado em respostas rápidas:

- **Quanto posso pagar por esta ação?** Preço-teto de Bazin (histórico), preço-teto projetivo e preço justo de Graham.
- **Ela é boa no conjunto?** Score Alpha de 0 a 100, aberto em 5 pilares auditáveis.
- **Vale mais que uma LCI isenta?** Simulador de renda fixa com IR regressivo e *gross-up* tributário.
- **O que esta notícia muda na minha carteira?** Radar com sentimento e cadeia de impacto setorial.
- **Me explica?** Copiloto que responde em português com os números calculados pelo backend.

> Projeto educativo. Nada aqui é recomendação de investimento.

## Funcionalidades

- **Visão geral** com Ibovespa, câmbio, juros, maiores altas e baixas, melhores Scores, oportunidades (preço abaixo do teto) e sua lista de favoritos
- **Mercado global:** bolsas do mundo, moedas, criptomoedas, commodities, juros dos EUA, termômetro de apetite a risco, gráfico juros × Ibovespa, expectativas do Boletim Focus e agenda econômica
- **Preço-teto:** Bazin, teto projetivo e Graham, com filtros por critérios (margem, dividend yield, ROE, setor), selo de margem positiva e favoritos
- **Dividendos:** ranking de dividend yield projetado e calculadora de renda passiva
- **Carteira:** posições, resultado, dividendos projetados e distribuição por setor (dados só no seu navegador)
- **Dossiê do ativo**, **renda fixa** (LCI, LCA, CDB e Tesouro), **radar de notícias** e **Analista IA**
- **Aprender:** passo a passo de decisão, glossário e dicas (?) ao lado de cada indicador
- Fundamentos reais (Yahoo Finance) com cache de 6 horas, tema claro e escuro OLED


---

## Arquitetura

```
┌──────────────────────────────┐        HTTP/JSON        ┌──────────────────────────────────────┐
│  Frontend  (Next.js 16)      │  ───────────────────▶   │  Backend  (Python 3.11+ / FastAPI)   │
│  TypeScript + Tailwind       │  localhost:3000 → 8000  │                                      │
│  Recharts + lucide-react     │                         │  engine/   matemática e regras        │
│                              │                         │   ├─ valuation.py    Graham, Bazin,   │
│  /dashboard                  │                         │   │                  projetivo, score │
│  /preco-teto                 │                         │   ├─ fixed_income.py LCI/LCA/CDB, IR  │
│  /ativo/[ticker]             │                         │   └─ ai_analyst.py   regras + Claude  │
│  /renda-fixa                 │                         │  services/ coleta de dados            │
│  /radar-noticias             │                         │   ├─ b3_service.py   yfinance, brapi  │
│  /analista-ia                │                         │   ├─ bcb_service.py  API SGS do BCB   │
└──────────────────────────────┘                         │   ├─ news_service.py sentimento+impacto│
                                                         │   └─ market_service.py cache+fallback │
                                                         │  data/fallback_b3.json (modo offline) │
                                                         └──────────────────────────────────────┘
```

**Princípio central:** toda conta acontece no Python. O frontend só exibe resultados prontos — o que deixa as regras de negócio testáveis, documentadas em `/docs` e independentes da interface.

**Resiliência:** se o Yahoo Finance, a brapi.dev ou o Banco Central falharem, o backend usa `data/fallback_b3.json` (46 ativos e 12 notícias de demonstração) e o frontend mostra o selo "Modo offline". Nenhuma falha externa vira erro 500.

---

## Como rodar

**Pré-requisitos:** Python 3.11+ e Node.js 20+.

### Um clique

- **Windows:** dê dois cliques em `iniciar_projeto.bat`.
- **Linux/macOS:** `chmod +x iniciar_projeto.sh && ./iniciar_projeto.sh`

O script cria o ambiente virtual, instala as dependências, sobe os dois servidores e abre o navegador.

### Manualmente

```bash
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

```bash
# Frontend (em outro terminal)
cd frontend
npm install
npm run dev
```

| Endereço | O que é |
|---|---|
| http://localhost:3000 | Dashboard |
| http://localhost:8000/docs | Documentação interativa da API (Swagger) — teste qualquer cálculo com um clique |

### Configuração opcional (`backend/.env`)

Copie `backend/.env.example` para `backend/.env`:

| Variável | Efeito |
|---|---|
| `ALPHARADAR_OFFLINE=1` | Força o modo offline (útil para apresentações sem internet) |
| `BRAPI_TOKEN` | Libera todos os tickers na brapi.dev (fonte secundária de cotações) |
| `NEWS_RSS_URLS` | Feeds RSS reais, separados por vírgula, no lugar das notícias de demonstração |
| `ANTHROPIC_API_KEY` | Ativa o Claude no Analista IA; sem ela, o motor de regras em Python responde |

---

## API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/overview` | Selic, CDI, IPCA, Ibovespa, dólar, maiores altas e baixas, cenário Bolsa × LCI/LCA e manchetes urgentes |
| GET | `/api/assets` | Os 46 ativos (36 da B3, entre ações e FIIs, e 10 dos EUA; filtre com `?mercado=B3` ou `?mercado=EUA`) com Score Alpha, preço-teto Bazin, projetivo e Graham |
| GET | `/api/mercado` | Bolsas, moedas, cripto, commodities, juros dos EUA, termômetro de apetite a risco e série juros × Ibovespa |
| GET | `/api/macro` | Expectativas do Boletim Focus (Selic, IPCA, PIB, câmbio) e agenda econômica da semana |
| GET | `/api/assets/{ticker}` | Dossiê: histórico de preços e dividendos, risco, score detalhado e notícias |
| POST | `/api/simulate/valuation` | Recalcula preço-teto e score com yield, payout e crescimento escolhidos |
| POST | `/api/simulate/fixed-income` | LCI/LCA × CDB × Tesouro Selic × dividendos, mês a mês |
| GET | `/api/news-radar` | Feed com sentimento, grau de impacto e ativos afetados |
| POST | `/api/ai/analyze` | Copiloto: risco, histórico, efeito dos juros e comparações |

---

## As fórmulas

| Métrica | Fórmula | Origem |
|---|---|---|
| Preço justo de Graham | √(22,5 × LPA × VPA) | Benjamin Graham, *The Intelligent Investor* (1949) |
| Preço-teto de Bazin | DPA dos últimos 12 meses ÷ yield exigido (6%) | Décio Bazin, *Faça Fortuna com Ações* (1992) |
| Preço-teto projetivo | LPA × (1 + g) × payout ÷ yield exigido | Extensão projetiva do método de Bazin |
| Margem de segurança | (preço-teto − cotação) ÷ cotação | Graham |
| Taxa CDB equivalente | taxa LCI ÷ (1 − alíquota de IR) | *Gross-up* tributário |
| Score Alpha | 5 pilares × 20 pontos: margem, dividend yield, ROE, dívida/EBITDA, notícias | Métrica autoral do projeto |

Fórmulas matemáticas são de domínio público (Lei 9.610/98, art. 8º, I). Código, nome, marca e interface deste projeto são originais.

---

## Fontes de dados

- [yfinance](https://pypi.org/project/yfinance/) — cotações, histórico e dividendos da B3 (sufixo `.SA`)
- [brapi.dev](https://brapi.dev/docs) — fonte secundária de cotações
- [API SGS do Banco Central](https://dadosabertos.bcb.gov.br/) — Selic (série 432), CDI (4389) e IPCA 12 meses (13522)

Fundamentos como LPA, VPA e ROE ficam em `fallback_b3.json` e mudam a cada balanço trimestral; a cotação é atualizada ao vivo (cache de 5 minutos).

---

## Testes e manutenção

```bash
cd backend
pip install -r requirements-dev.txt
pytest                                  # 81 testes: motores, API e segurança (offline, sem chaves)
python scripts/atualizar_fallback.py    # atualiza o catálogo de reserva com dados reais do Yahoo
python scripts/verificar_segredos.py    # procura chaves e arquivos sensíveis nos arquivos versionados
```

O GitHub Actions (`.github/workflows/ci.yml`) roda a varredura de segredos, os testes e o `pip-audit` do backend, e o lint, o build e o `npm audit` do frontend a cada envio. Veja o [SECURITY.md](SECURITY.md) para as defesas de segurança.

---

## Publicar na Railway

O projeto tem dois serviços no mesmo repositório: a API Python e o site Next.js.

**1. Serviço da API (`backend`)**
1. Na Railway: **New Project → Deploy from GitHub repo** e escolha este repositório.
2. Em **Settings → Source → Root Directory**, defina `/backend`. O `railway.json` já traz o comando de início e o teste de saúde (`/api/health`).
3. Em **Settings → Networking**, clique em **Generate Domain** e copie o endereço (algo como `https://alpharadar-api.up.railway.app`).
4. Em **Variables**, adicione (todas opcionais): `GROQ_API_KEY`, `GEMINI_API_KEY`, `NEWS_RSS_URLS` e as chaves de notícias do `backend/.env.example`. O CORS libera só o site da demonstração e o ambiente local; no seu fork, defina `CORS_ORIGINS` com o endereço do seu site.

**2. Serviço do site (`frontend`)**
1. No mesmo projeto: **New → GitHub Repo** (o mesmo repositório) e defina o Root Directory como `/frontend`.
2. Em **Variables**, defina `NEXT_PUBLIC_API_URL` com o endereço da API do passo anterior, **sem barra no final**. Faça isso antes do build: o Next.js grava esse valor no código ao compilar.
3. Gere o domínio público em **Settings → Networking**.

Observações: o Yahoo Finance pode bloquear servidores em nuvem; nesse caso o app mostra os dados de reserva com o selo "Modo offline". A rota de IA aceita 8 perguntas por minuto por IP (`AI_RATE_LIMIT_PER_MINUTE`) e 60 no total (`AI_GLOBAL_RATE_LIMIT_PER_MINUTE`) para proteger a cota gratuita.

---

## Stack

**Backend:** Python, FastAPI, Uvicorn, pandas, NumPy, yfinance, requests, defusedxml, SDK da Anthropic (opcional)
**Frontend:** Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, Recharts, lucide-react

Para entender cada arquivo do backend em detalhe, leia o [GUIA_ESTUDO_ENTREVISTA.md](GUIA_ESTUDO_ENTREVISTA.md).

---

## Autor — Gabriel Bernardino (Gabriel Bernardino dos Santos)

Projeto desenvolvido por **Gabriel Bernardino** (**Gabriel Bernardino dos Santos**), 17 anos (nascido em 12/05/2009), desenvolvedor de software em formação e estudante de **Engenharia de Software na UniSenai** em **Londrina/PR**.

- **Área de atuação:** Desenvolvimento back-end com Python, FastAPI, análise de dados com pandas e IA aplicada.
- **Certificação:** Python Development — FIAP (80 horas).
- **Objetivo atual:** Buscando 1ª oportunidade em TI (Estágio ou Jovem Aprendiz, 100% remoto).
- **LinkedIn:** [linkedin.com/in/gabrielbersantos](https://www.linkedin.com/in/gabrielbersantos)
- **GitHub:** [github.com/Bersdev](https://github.com/Bersdev)
- **Site Oficial / Portfólio:** [bersdev.github.io](https://bersdev.github.io)
- **E-mail:** [bernardinogabriel68@gmail.com](mailto:bernardinogabriel68@gmail.com)

---

## Créditos

Icones 3D: [Fluent Emoji](https://github.com/microsoft/fluentui-emoji) da Microsoft, licença MIT. Fontes de dados: veja a seção "Fontes de dados".
