# Guia de estudo do AlphaRadar B3

Este guia explica, arquivo por arquivo, o backend em Python. A ideia é que você consiga abrir cada arquivo, entender o que ele faz e explicar numa entrevista com as suas palavras.

**Ordem de leitura recomendada:**

1. `engine/valuation.py` — a matemática mais importante, sem dependências externas
2. `engine/fixed_income.py` — renda fixa e pandas
3. `services/bcb_service.py` e `services/b3_service.py` — como buscar dados na internet
4. `services/market_service.py` — cache e fallback (resiliência)
5. `services/news_service.py` — classificação de texto e regras de negócio
6. `engine/ai_analyst.py` — roteamento de intenções e integração com LLM
7. `main.py` — como tudo vira uma API HTTP

Para experimentar cada módulo isolado, entre na pasta `backend` com o ambiente virtual ativo:

```bash
python -m engine.valuation      # roda os exemplos (doctests) das fórmulas
python -m engine.fixed_income   # roda uma simulação de LCI × CDB
```

---

## 1. `engine/valuation.py` — preço-teto, Graham e Score Alpha

### O que faz
Recebe os números de uma empresa (cotação, LPA, VPA, dividendos, payout, ROE, dívida) e devolve quanto ela "vale" segundo três métodos clássicos, mais uma nota de 0 a 100.

### Conceitos que você precisa dominar

| Sigla | Significado | Exemplo |
|---|---|---|
| LPA | Lucro por ação = lucro líquido ÷ número de ações | Lucro de R$ 10 bi ÷ 2 bi de ações = R$ 5 |
| VPA | Valor patrimonial por ação = patrimônio líquido ÷ ações | |
| DPA | Dividendos por ação pagos no período | |
| Payout | Percentual do lucro distribuído | LPA 5 e DPA 2,5 → payout 50% |
| Dividend yield | DPA ÷ cotação | R$ 2 ÷ R$ 40 = 5% |

### As funções

- **`preco_justo_graham(lpa, vpa)`** — `sqrt(22.5 * lpa * vpa)`. O 22,5 vem de P/L máximo de 15 vezes P/VP máximo de 1,5. Retorna `None` se LPA ou VPA forem negativos (não existe raiz real e, conceitualmente, Graham não avalia empresa com prejuízo).
- **`preco_teto_bazin_historico(dpa_12m, yield_min)`** — dividendos dos últimos 12 meses ÷ 6%. Pergunta respondida: "qual o preço máximo para receber pelo menos 6% ao ano?".
- **`dpa_projetado(...)` e `preco_teto_projetivo(...)`** — em vez de olhar o passado, estima o dividendo futuro: `LPA × (1 + g) × payout`. Isso corrige distorções de lucros atípicos.
- **`margem_seguranca(preco_teto, cotacao)`** — positivo significa que a ação está abaixo do teto (desconto).
- **`calcular_score_alpha(ativo, sentimento)`** — 5 pilares de 20 pontos. Cada indicador vira pontos por **interpolação linear** (função `_escala_linear`): abaixo do "pior" valor = 0, acima do "melhor" = 20, no meio, proporcional.

### Decisões de design para comentar
- **Dataclasses** (`Pilar`, `ScoreAlpha`) deixam o resultado tipado e com método `to_dict()` para virar JSON.
- **Indicador que não se aplica não é punido:** bancos e FIIs não usam Dívida/EBITDA, então recebem nota neutra (14 de 20) com a explicação escrita.
- **FIIs usam yield de referência de 8%** (`yield_padrao`), porque distribuem quase todo o resultado e quase não crescem; e Graham não é calculado para fundos.
- **Doctests:** os exemplos dentro das docstrings (`>>> preco_teto_bazin_historico(1.2, 0.06)`) são testes executáveis.

**Como explicar:** "Implementei as fórmulas como funções puras, sem acesso a rede ou banco. Isso torna o motor fácil de testar e reutilizar: a mesma função atende a tabela, o simulador e o copiloto."

---

## 2. `engine/fixed_income.py` — LCI, LCA, CDB e gross-up

### O que faz
Simula, mês a mês, quanto rende o mesmo dinheiro em LCI, LCA, CDB, Tesouro Selic e dividendos reinvestidos, já descontando o Imposto de Renda.

### Pontos-chave
- **Tabela regressiva de IR:** `aliquota_ir(dias)` percorre `TABELA_IR_REGRESSIVA` (22,5% até 180 dias; 20% até 360; 17,5% até 720; 15% acima).
- **Gross-up:** `taxa_cdb_equivalente(taxa_lci, dias) = taxa_lci / (1 - aliquota)`. Uma LCI de 92% do CDI por 2 anos equivale a um CDB de 92 ÷ 0,825 ≈ 111,5% do CDI.
- **Conversão de taxas:** `anual_para_mensal` usa juros compostos: `(1 + i_anual)^(1/12) − 1` (não é só dividir por 12).
- **Cada aporte é um "lote":** em `_curva_tributada`, o IR de cada aporte depende de quanto tempo *aquele* dinheiro ficou aplicado — igual ao banco faz.
- **pandas:** o resultado mensal vira um `DataFrame` e depois `df.to_dict(orient="records")`, o formato que o gráfico do frontend consome.
- **Simplificações documentadas no topo do arquivo** (CDI constante, IOF ignorado, mês de 30 dias). Saber dizer as limitações do seu modelo é um ponto forte em entrevista.

---

## 3. `services/bcb_service.py` — Selic, CDI e IPCA do Banco Central

- Chama a API pública SGS: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados/ultimos/1?formato=json`.
- Séries: **432** (meta Selic), **4389** (CDI anualizado), **13522** (IPCA acumulado em 12 meses).
- `requests.get(..., timeout=6)` e `raise_for_status()`: nunca fazer requisição sem timeout; erro HTTP vira exceção.
- Se uma série falhar, as outras continuam valendo.

**Por que não usei a biblioteca `python-bcb`?** Ela encapsula exatamente essa API. Chamando direto, o projeto tem uma dependência a menos e o funcionamento fica visível para estudo.

---

## 4. `services/b3_service.py` — cotações via yfinance e brapi

- `para_yahoo("PETR4")` → `"PETR4.SA"`: o Yahoo identifica ações brasileiras com o sufixo `.SA`.
- `cotacoes_yfinance` baixa os últimos 5 pregões de todos os tickers numa única chamada (`yf.download`) e calcula a variação do dia comparando os dois últimos fechamentos.
- `historico_yfinance` traz 1 ano de preços e os dividendos; soma os dos últimos 365 dias para obter o DPA de 12 meses real.
- `_com_timeout` roda a chamada numa thread separada (`ThreadPoolExecutor`) e desiste depois de 12 s — o yfinance não tem timeout próprio confiável.
- `cotacoes_brapi` é a fonte secundária.

**Decisão importante:** este módulo *pode* lançar exceção. Quem decide o que fazer quando falha é o `market_service`. Cada camada tem uma responsabilidade (princípio da responsabilidade única).

---

## 5. `services/market_service.py` — cache e fallback

É a única porta de entrada de dados para o resto do sistema.

- **Fallback:** toda chamada externa fica dentro de `try/except`. Se falhar, usa `data/fallback_b3.json` e marca `fonte = "fallback"`, que o frontend exibe como "Modo offline".
- **Cache com TTL** (`CacheTTL`): guarda o resultado por 5 min (cotações), 30 min (macro) ou 1 h (histórico). Evita lentidão e bloqueio por excesso de requisições. Usa `threading.Lock` porque o FastAPI atende requisições em paralelo.
- **`copy.deepcopy`** ao devolver dados do cache: impede que uma rota altere sem querer o dado guardado.
- **`_historico_sintetico`:** sem internet, gera um gráfico ilustrativo por passeio aleatório com semente fixa (`zlib.crc32(ticker)`), que sempre termina na cotação atual. Mesma semente, mesmo gráfico.
- **`estatisticas_risco`** (pandas):
  - volatilidade anual = desvio-padrão dos retornos diários × √252 (dias úteis no ano)
  - *drawdown* máximo = maior queda de um topo até um fundo: `(serie / serie.cummax() - 1).min()`
- **Juro real** pela fórmula de Fisher: `(1 + Selic) / (1 + IPCA) − 1`.

**Como explicar:** "Programei o backend para nunca cair por causa de terceiros. Se o Yahoo ou o Banco Central estiverem fora, o usuário continua vendo dados, com um aviso claro de que estão offline."

---

## 6. `services/news_service.py` — sentimento e cadeia de impacto

- **Sentimento por léxico:** conta palavras positivas e negativas (`PALAVRAS_POSITIVAS` / `NEGATIVAS`) no texto sem acentos. Índice = (pos − neg) ÷ (pos + neg). É uma técnica clássica de processamento de linguagem natural, simples e explicável.
- **`MATRIZ_IMPACTO`:** o coração das regras de negócio. Para cada tema (Selic em alta, petróleo em queda, dólar em alta...) há palavras-gatilho, quem ganha, quem perde e o efeito na renda fixa. Cada regra traz um comentário com a lógica econômica — por exemplo, juros altos favorecem bancos e FIIs de papel (CRIs indexados ao CDI).
- **`sentimento_por_ativo`:** soma +peso quando o ativo é beneficiado e −peso quando é prejudicado (alto = 1, médio = 0,6, baixo = 0,3) e passa o total por `tanh` para ficar entre −1 e +1. Esse valor alimenta o 5º pilar do Score Alpha.
- **RSS opcional:** com `NEWS_RSS_URLS` no `.env`, manchetes reais passam pelo mesmo classificador. O XML é lido com `defusedxml`, que protege contra ataques de XML malicioso (XXE e "billion laughs") — conteúdo externo nunca deve ser parseado com o parser padrão.

---

## 7. `engine/ai_analyst.py` — o copiloto

Dois modos:

1. **Motor de regras (padrão, gratuito):** `motor_de_regras` identifica a intenção pela pergunta e escolhe um relatório:
   - cita LCI/LCA → `relatorio_comparacao_lci` (extrai o "92%" com expressão regular)
   - fala de Selic ou juros → `relatorio_tema_selic` (detecta se é alta ou queda)
   - cita um ticker → `relatorio_ativo` (histórico, valuation, risco, pontos fortes e de atenção)
   - nenhum dos casos → `relatorio_panorama`
2. **Claude (opcional):** com `ANTHROPIC_API_KEY`, os *mesmos números* são enviados ao modelo pelo SDK oficial da Anthropic, que redige a análise. O prompt de sistema proíbe inventar números e fazer recomendação personalizada.

**Decisões para comentar:**
- **Quem calcula é o Python; o LLM só interpreta.** Isso evita "alucinação" de números.
- **Degradação elegante:** qualquer erro na chamada da IA (sem rede, sem crédito, recusa do modelo) cai no motor de regras, sem erro para o usuário.
- O resultado tem formato fixo (`titulo`, `resumo`, `secoes`), então o frontend renderiza igual nos dois modos.

---

## 8. `main.py` — a API FastAPI

- **Pydantic** (`SimulacaoValuation`, `SimulacaoRendaFixa`, `PerguntaIA`) valida a entrada automaticamente: `Field(ge=0.01, le=0.30)` rejeita um yield de 50% com erro 422 antes de chegar na matemática.
- **CORS** libera o frontend em `localhost:3000` a chamar a API em `localhost:8000`.
- **`@app.exception_handler(Exception)`**: rede de segurança — qualquer erro inesperado vira resposta 503 amigável e é registrado no log.
- **`load_dotenv()`** antes dos imports dos serviços, para as variáveis do `.env` já valerem.
- **`/docs`** é gerado automaticamente a partir das rotas, tipos e docstrings.

---

## Perguntas prováveis na entrevista

**Por que Python no backend e não tudo em JavaScript?**
O ecossistema de dados e finanças do Python (pandas, NumPy, yfinance) é o mais maduro, e o FastAPI dá validação e documentação automáticas. O frontend só exibe resultados — a regra de negócio fica num lugar só.

**O que acontece se o Yahoo Finance sair do ar?**
O `market_service` captura a exceção, devolve o `fallback_b3.json` e marca a fonte como offline. O frontend mostra o selo "Modo offline". Para demonstrar, defino `ALPHARADAR_OFFLINE=1`.

**Como você garante que as fórmulas estão certas?**
São funções puras com doctests; comparei com exemplos calculados à mão (ex.: DPA de R$ 1,20 ÷ 6% = R$ 20,00) e cada parte do Score mostra o indicador e a explicação.

**Quais as limitações?**
Fundamentos (LPA, VPA, ROE) ficam num arquivo e precisam ser atualizados a cada balanço; o crescimento *g* é uma premissa; o simulador de renda fixa supõe CDI constante; o classificador de sentimento por palavras não entende ironia ou contexto. Próximos passos: buscar fundamentos nos dados abertos da CVM, adicionar testes com `pytest` e persistir histórico num banco.

**Isso é plágio de algum site?**
Não. As fórmulas de Graham e Bazin são métodos matemáticos publicados, sem proteção autoral (Lei 9.610/98, art. 8º, I). Nome, código, textos, interface e o Score Alpha são autorais; os dados vêm de fontes públicas.
