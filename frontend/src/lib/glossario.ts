// Glossário do AlphaRadar: usado nas dicas (?) ao lado dos indicadores e na página Aprender.
// Texto educativo e simplificado: não substitui a leitura dos relatórios das empresas.

export interface Termo {
  nome: string;
  curto: string;
  longo: string;
  formula?: string;
  grupo: "Valuation" | "Indicadores da empresa" | "Risco" | "Renda fixa e juros" | "Mercado global";
}

export const GLOSSARIO = {
  preco_teto: {
    nome: "Preço-teto",
    grupo: "Valuation",
    curto: "O preço máximo que você aceitaria pagar para ter o retorno em dividendos que exige. Cotação abaixo do teto = há margem; acima = sem margem.",
    longo:
      "É um limite de preço, não uma previsão. Você define quanto de dividendo anual exige (por exemplo, 6%) e o método diz até que cotação isso se sustenta. Comprar acima do teto não significa que a empresa é ruim: apenas que o preço já embute um retorno menor que o exigido.",
    formula: "Preço-teto = dividendos por ação ÷ yield exigido",
  },
  bazin: {
    nome: "Preço-teto de Bazin",
    grupo: "Valuation",
    curto: "Usa os dividendos que a empresa JÁ pagou nos últimos 12 meses, divididos pelo yield mínimo (6% ao ano no método original).",
    longo:
      "Criado por Décio Bazin (livro \"Faça Fortuna com Ações\", 1992). Olha para trás: se a empresa teve um ano atípico de dividendos, o teto fica distorcido. Por isso o AlphaRadar mostra também o teto projetivo.",
    formula: "Teto = dividendos dos últimos 12 meses ÷ 6%",
  },
  preco_teto_projetivo: {
    nome: "Preço-teto projetivo",
    grupo: "Valuation",
    curto: "Igual ao de Bazin, mas usa o dividendo ESTIMADO para os próximos 12 meses (lucro × crescimento × payout).",
    longo:
      "Olha para frente: projeta o lucro por ação com um crescimento esperado e aplica o payout (parte do lucro distribuída). Depende de premissas: mude os controles de crescimento, payout e yield para ver como o teto reage. Crescimento é palpite, então teste cenários conservadores.",
    formula: "Teto projetivo = LPA × (1 + crescimento) × payout ÷ yield exigido",
  },
  graham: {
    nome: "Preço justo de Graham",
    grupo: "Valuation",
    curto: "Estimativa de valor para empresas com lucro e patrimônio positivos. Não se aplica a prejuízo nem a FIIs.",
    longo:
      "Proposto por Benjamin Graham (\"O Investidor Inteligente\", 1949). O 22,5 vem de um P/L máximo de 15 vezes um P/VP máximo de 1,5. Funciona melhor em empresas maduras e estáveis; em empresas de crescimento acelerado costuma parecer baixo demais.",
    formula: "√(22,5 × LPA × VPA)",
  },
  margem_seguranca: {
    nome: "Margem de segurança",
    grupo: "Valuation",
    curto: "Quanto o preço-teto está acima (positiva, verde) ou abaixo (negativa) da cotação atual.",
    longo:
      "Conceito de Graham: comprar com folga para absorver erros de estimativa. Margem positiva sugere que o preço está dentro do limite que você definiu; margem negativa pede paciência ou premissas diferentes. É um critério entre vários, nunca o único.",
    formula: "(preço-teto − cotação) ÷ cotação",
  },
  score_alpha: {
    nome: "Score Alpha",
    grupo: "Valuation",
    curto: "Nota de 0 a 100 do AlphaRadar: 5 pilares de 20 pontos (margem, dividendos, rentabilidade, dívida e notícias).",
    longo:
      "Métrica própria do projeto, desenhada para ser auditável: cada pilar mostra o indicador que gerou a nota. Serve para ordenar e filtrar ideias, não para decidir sozinha. Bancos, seguradoras e FIIs recebem nota neutra no pilar de dívida porque o indicador não se aplica a eles.",
  },
  dividend_yield: {
    nome: "Dividend Yield (DY)",
    grupo: "Indicadores da empresa",
    curto: "Dividendos pagos em 12 meses em relação à cotação. DY de 8% significa R$ 8 por ano para cada R$ 100 investidos.",
    longo:
      "O DY cai quando a cotação sobe e sobe quando ela cai, então um DY muito alto às vezes é sinal de preço em queda. Compare o DY projetado (estimativa para o ano) com o histórico e sempre com a renda fixa isenta.",
    formula: "DY = dividendos por ação (12 meses) ÷ cotação",
  },
  payout: {
    nome: "Payout",
    grupo: "Indicadores da empresa",
    curto: "Percentual do lucro que a empresa distribui como dividendos.",
    longo:
      "Payout muito alto (perto de 100%) deixa pouco para reinvestir; muito baixo indica empresa que prefere crescer. Fundos imobiliários distribuem, por regra, ao menos 95% do resultado semestral.",
    formula: "Payout = dividendos ÷ lucro",
  },
  lpa: {
    nome: "LPA (lucro por ação)",
    grupo: "Indicadores da empresa",
    curto: "Lucro líquido dos últimos 12 meses dividido pelo número de ações.",
    longo: "É a base para projetar dividendos: quanto mais lucro por ação, mais a empresa tem para distribuir.",
    formula: "LPA = lucro líquido ÷ número de ações",
  },
  vpa: {
    nome: "VPA (valor patrimonial por ação)",
    grupo: "Indicadores da empresa",
    curto: "Patrimônio líquido dividido pelo número de ações: o valor contábil de cada ação.",
    longo: "Mostra o que sobraria, em termos contábeis, para cada ação se a empresa fosse encerrada. O valor contábil nem sempre reflete o valor de mercado dos ativos.",
    formula: "VPA = patrimônio líquido ÷ número de ações",
  },
  pl: {
    nome: "P/L (preço sobre lucro)",
    grupo: "Indicadores da empresa",
    curto: "Quantos anos de lucro atual o preço paga. P/L 10 = a cotação equivale a 10 anos do lucro de hoje.",
    longo:
      "Quanto menor, mais barata a ação em relação ao lucro, mas o que é barato varia por setor: empresas de crescimento têm P/L alto, e P/L muito baixo pode indicar que o mercado espera queda no lucro. Não existe quando há prejuízo.",
    formula: "P/L = cotação ÷ LPA",
  },
  pvp: {
    nome: "P/VP (preço sobre valor patrimonial)",
    grupo: "Indicadores da empresa",
    curto: "Compara a cotação com o patrimônio contábil. Abaixo de 1, a ação negocia abaixo do patrimônio.",
    longo: "Para FIIs é muito usado: cotas abaixo de 1 negociam com desconto sobre o patrimônio do fundo. Para bancos também é a principal referência de preço. Atenção a patrimônios que não refletem a realidade dos ativos.",
    formula: "P/VP = cotação ÷ VPA",
  },
  roe: {
    nome: "ROE (retorno sobre o patrimônio)",
    grupo: "Indicadores da empresa",
    curto: "Quanto a empresa lucra a cada R$ 100 de patrimônio. ROE de 18% = R$ 18 de lucro por ano.",
    longo: "Mede eficiência. Acima de 15% costuma ser considerado bom, mas ROE inflado por muita dívida é armadilha: confira o endividamento. Empresas com patrimônio muito pequeno podem ter ROE artificialmente enorme.",
    formula: "ROE = lucro líquido ÷ patrimônio líquido",
  },
  divida_ebitda: {
    nome: "Dívida líquida / EBITDA",
    grupo: "Risco",
    curto: "Em quantos anos a geração de caixa operacional pagaria a dívida líquida. Negativo = tem mais caixa que dívida.",
    longo:
      "Até 2x é confortável para a maioria dos setores; acima de 3x pede atenção, principalmente se os juros estão altos. Não se aplica a bancos e seguradoras, e setores como energia e saneamento toleram mais dívida por terem receita previsível.",
    formula: "(dívida bruta − caixa) ÷ EBITDA",
  },
  beta: {
    nome: "Beta",
    grupo: "Risco",
    curto: "Sensibilidade da ação ao mercado. Beta 1,5 tende a oscilar uma vez e meia o Ibovespa; beta 0,5, metade.",
    longo: "É calculado a partir do histórico, então muda com o tempo. Beta baixo não é sinônimo de segurança, apenas de menor correlação com o mercado.",
  },
  volatilidade: {
    nome: "Volatilidade anual",
    grupo: "Risco",
    curto: "O quanto o preço oscila ao longo do ano (desvio-padrão dos retornos diários, anualizado).",
    longo: "Volatilidade de 30% significa que oscilações de cerca de 30% para cima ou para baixo em um ano são comuns. Quanto maior, mais estômago o investidor precisa ter.",
    formula: "desvio-padrão dos retornos diários × √252",
  },
  drawdown: {
    nome: "Maior queda (drawdown)",
    grupo: "Risco",
    curto: "A maior queda do topo até o fundo no período de 12 meses.",
    longo: "Mostra a pior sequência recente. Pergunte-se: eu manteria a posição se o investimento caísse isso?",
  },
  selic: {
    nome: "Selic",
    grupo: "Renda fixa e juros",
    curto: "A taxa básica de juros, definida pelo Copom. É a referência de todo o crédito e da renda fixa do país.",
    longo: "Juros altos tornam a renda fixa mais atraente e pressionam o valor de empresas endividadas e de crescimento. Juros caindo costumam favorecer a bolsa e os fundos imobiliários de tijolo.",
  },
  cdi: {
    nome: "CDI",
    grupo: "Renda fixa e juros",
    curto: "Taxa dos empréstimos entre bancos, quase igual à Selic. Os investimentos pós-fixados pagam um percentual dela (ex.: 100% do CDI).",
    longo: "\"CDB a 110% do CDI\" significa que paga 1,1 vez o CDI no ano.",
  },
  ipca: {
    nome: "IPCA",
    grupo: "Renda fixa e juros",
    curto: "A inflação oficial. Rendimento só é ganho de verdade se supera o IPCA.",
    longo: "O Tesouro IPCA+ paga a inflação mais uma taxa fixa, protegendo o poder de compra.",
  },
  juro_real: {
    nome: "Juro real",
    grupo: "Renda fixa e juros",
    curto: "Selic descontada a inflação: o ganho acima dos preços.",
    longo: "Juro real alto torna a renda fixa uma concorrente forte da bolsa: a ação precisa oferecer retorno bem maior para compensar o risco.",
    formula: "(1 + Selic) ÷ (1 + IPCA) − 1",
  },
  lci_lca: {
    nome: "LCI e LCA",
    grupo: "Renda fixa e juros",
    curto: "Letras de crédito imobiliário e do agronegócio: isentas de Imposto de Renda para pessoa física e cobertas pelo FGC.",
    longo: "O FGC garante até R$ 250 mil por CPF e por instituição financeira. A isenção de IR faz a LCI render mais que um CDB de mesma taxa bruta; compare sempre pela taxa equivalente (gross-up).",
  },
  gross_up: {
    nome: "Taxa CDB equivalente (gross-up)",
    grupo: "Renda fixa e juros",
    curto: "Quanto um CDB precisa pagar para empatar com uma LCI/LCA isenta, depois do Imposto de Renda.",
    longo: "Quanto mais curto o prazo, maior o IR do CDB e maior a vantagem da LCI. Acima de 720 dias o IR cai para 15%.",
    formula: "taxa da LCI ÷ (1 − alíquota de IR)",
  },
  ir_regressivo: {
    nome: "IR regressivo",
    grupo: "Renda fixa e juros",
    curto: "Imposto sobre o rendimento: 22,5% até 180 dias, 20% até 360, 17,5% até 720 e 15% acima disso.",
    longo: "O imposto incide só sobre o lucro, e o tempo de aplicação de CADA depósito é o que conta.",
  },
  fii: {
    nome: "Fundo imobiliário (FII)",
    grupo: "Indicadores da empresa",
    curto: "Fundo que investe em imóveis ou títulos imobiliários e distribui ao menos 95% do resultado aos cotistas, em geral todo mês.",
    longo: "Os rendimentos mensais costumam ser isentos de IR para pessoa física, mas não são garantidos: dependem de aluguéis, vacância e inadimplência. Ganho de capital na venda das cotas é tributado.",
  },
  dividendos_eua: {
    nome: "Dividendos de ações dos EUA",
    grupo: "Indicadores da empresa",
    curto: "Brasileiros têm 30% de imposto retido na fonte sobre dividendos de empresas americanas.",
    longo: "Na B3 também é possível comprar BDRs dessas empresas (ex.: NVDC34, MSFT34, AAPL34), sem conta no exterior, com regras tributárias próprias.",
  },
  vix: {
    nome: "VIX (índice do medo)",
    grupo: "Mercado global",
    curto: "Mede a volatilidade esperada do S&P 500. Acima de 25 indica nervosismo; abaixo de 16, calma.",
    longo: "Quando o VIX dispara, o mercado global tende a buscar proteção, o que costuma enfraquecer bolsas emergentes e o real.",
  },
  treasury: {
    nome: "Juros dos EUA (Treasuries)",
    grupo: "Mercado global",
    curto: "Rendimento dos títulos do governo americano: a referência de \"taxa livre de risco\" do mundo.",
    longo: "Quando sobe, capital estrangeiro tem uma alternativa segura mais paga e tende a sair de bolsas emergentes. É uma das relações mais observadas entre juros e bolsa.",
  },
  dxy: {
    nome: "Índice do dólar (DXY)",
    grupo: "Mercado global",
    curto: "Força do dólar contra uma cesta de moedas. Dólar forte no mundo costuma pressionar emergentes.",
    longo: "O real não segue só o DXY, porque também depende de juros, política fiscal e commodities.",
  },
  focus: {
    nome: "Boletim Focus",
    grupo: "Mercado global",
    curto: "Pesquisa semanal do Banco Central com as projeções de economistas para Selic, inflação, PIB e câmbio.",
    longo: "É a melhor referência gratuita do que o mercado espera para os juros (os juros futuros precificam o mesmo, em outra métrica). Mostra a mediana das projeções e a faixa entre mínima e máxima.",
  },
  risk_on_off: {
    nome: "Apetite a risco (risk-on / risk-off)",
    grupo: "Mercado global",
    curto: "Leitura do dia: investidores buscam ativos de risco (risk-on) ou se protegem (risk-off).",
    longo: "O termômetro do AlphaRadar combina VIX, S&P 500, dólar global e Ibovespa. Descreve o dia, não prevê o futuro.",
  },
} satisfies Record<string, Termo>;

export type ChaveTermo = keyof typeof GLOSSARIO;
