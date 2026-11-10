// Cliente da API Python (FastAPI). Toda a matemática acontece no backend;
// o frontend só busca os resultados prontos e os exibe.

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {}

export async function api<T>(path: string, body?: unknown): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(`${API_URL}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      `Não foi possível conectar ao backend em ${API_URL}. Inicie o servidor Python com "uvicorn main:app --port 8000" na pasta backend.`,
    );
  }
  if (!resp.ok) {
    const dados = await resp.json().catch(() => ({}));
    throw new ApiError(dados.detail ?? dados.erro ?? `Erro ${resp.status} ao consultar ${path}.`);
  }
  return resp.json() as Promise<T>;
}

// ---------------- Tipos (espelham as respostas do backend) ----------------

export type Fonte = "ao_vivo" | "fallback" | "misto";

export interface Pilar {
  nome: string;
  pontos: number;
  maximo: number;
  valor_base: number | null;
  explicacao: string;
}

export interface Score {
  total: number;
  classificacao: string;
  pilares: Pilar[];
}

export interface Ativo {
  ticker: string;
  nome: string;
  tipo: "acao" | "fii";
  mercado: "B3" | "EUA";
  moeda: "BRL" | "USD";
  cotacao_brl?: number;
  setor: string;
  cotacao: number;
  variacao_dia: number;
  lpa: number;
  vpa: number;
  dpa_12m: number;
  payout_medio: number;
  crescimento_lucro: number;
  roe: number;
  divida_liquida_ebitda: number | null;
  pl: number | null;
  pvp: number | null;
  beta: number;
  fonte_cotacao?: Fonte;
}

export interface Valuation {
  ticker: string;
  cotacao: number;
  premissas: { yield_desejado: number; crescimento_g: number; payout_pct: number };
  preco_justo_graham: number | null;
  preco_teto_bazin: number | null;
  preco_teto_projetivo: number | null;
  margem_graham: number | null;
  margem_bazin: number | null;
  margem_projetiva: number | null;
  dpa_12m: number;
  dpa_projetado: number;
  dy_atual: number;
  dy_projetado: number;
  score: Score;
}

export type AtivoAvaliado = Ativo & Valuation & { sentimento_noticias: number };

export interface Macro {
  selic_anual: number;
  cdi_anual: number;
  ipca_12m: number;
  dolar: number;
  dolar_var: number;
  ibovespa: number;
  ibovespa_var: number;
  ifix: number;
  ifix_var: number;
  sp500: number;
  sp500_var: number;
  petroleo_brent: number;
  petroleo_brent_var: number;
  juro_real: number;
  fontes: { bcb: Fonte; mercado: Fonte };
}

export interface AtivoAfetado {
  ticker: string;
  nome: string;
  efeito: "beneficiado" | "prejudicado";
}

export interface Noticia {
  id: string;
  titulo: string;
  resumo: string;
  categoria: string;
  data: string;
  link?: string;
  sentimento: number;
  sentimento_rotulo: "Positivo" | "Neutro" | "Negativo";
  impacto: "alto" | "medio" | "baixo";
  beneficiados: string[];
  prejudicados: string[];
  setores: string[];
  renda_fixa: string;
  fonte: string;
  origem?: string;
  ativos_afetados: AtivoAfetado[];
  efeito_no_ativo?: "beneficiado" | "prejudicado";
}

export interface ResumoAtivo {
  ticker: string;
  nome: string;
  tipo: string;
  mercado?: "B3" | "EUA";
  moeda?: "BRL" | "USD";
  cotacao: number;
  variacao_dia: number;
}

export interface Overview {
  macro: Macro;
  fonte_cotacoes: Fonte;
  atualizado_em: string;
  maiores_altas: ResumoAtivo[];
  maiores_baixas: ResumoAtivo[];
  cenario: {
    lci_92_cdi: number;
    cdb_equivalente_lci_92: number;
    dy_medio_fiis: number;
    dy_medio_acoes: number;
    premio_fii_vs_lci: number;
    leitura: string;
  };
  manchetes_urgentes: Noticia[];
  ticker_tape: ResumoAtivo[];
}

export interface PremioLci {
  dy_projetado_pct: number;
  rendimento_lci_pct: number;
  premio_pp: number;
  leitura: string;
}

export interface DetalheAtivo {
  ativo: Ativo;
  valuation: Valuation;
  historico: {
    precos: { data: string; fechamento: number }[];
    dividendos: { data: string; valor: number }[];
    dpa_12m: number;
    fonte: Fonte;
  };
  risco: { volatilidade_anual: number | null; max_drawdown: number | null; retorno_periodo: number | null };
  premio_lci: PremioLci;
  noticias: Noticia[];
  sentimento_noticias: number;
}

export interface ProdutoRF {
  produto: string;
  taxa: string;
  isento_ir: boolean;
  valor_final_liquido: number;
  lucro_liquido: number;
  rentabilidade_pct: number;
}

export interface SimulacaoRF {
  prazo_dias: number;
  aliquota_ir_prazo: number;
  gross_up: {
    lci_cdb_equivalente_pct_cdi: number;
    lca_cdb_equivalente_pct_cdi: number;
    cdb_lci_equivalente_pct_cdi: number;
    explicacao: string;
  };
  economia_ir_lci: number;
  total_investido: number;
  produtos: ProdutoRF[];
  melhor_opcao: string;
  curva_mensal: {
    mes: number;
    investido: number;
    lci: number;
    lca: number;
    cdb_bruto: number;
    cdb_liquido: number;
    tesouro_selic_liquido: number;
    dividendos_reinvestidos: number;
  }[];
}

export interface RespostaIA {
  pergunta: string;
  modo: "regras" | "llm";
  provedor: string | null;
  titulo: string;
  resumo: string;
  secoes: { titulo: string; itens: string[] }[];
  ativos: string[];
  texto_llm: string | null;
  aviso: string;
  aviso_llm?: string;
}

// ---------------- Formatação pt-BR ----------------

const brl = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const num = (casas: number) =>
  new Intl.NumberFormat("pt-BR", { minimumFractionDigits: casas, maximumFractionDigits: casas });

export const fmtBRL = (v: number | null | undefined) => (v == null ? "—" : brl.format(v));
const usd = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "USD" });
/** Preço na moeda do ativo: R$ para a B3, US$ para os EUA. */
export const fmtPreco = (v: number | null | undefined, moeda: string = "BRL") =>
  v == null ? "—" : moeda === "USD" ? usd.format(v) : brl.format(v);
export const fmtNum = (v: number | null | undefined, casas = 2) => (v == null ? "—" : num(casas).format(v));
export const fmtPct = (v: number | null | undefined, casas = 1) => (v == null ? "—" : `${num(casas).format(v)}%`);
export const fmtSinal = (v: number | null | undefined, casas = 2) => {
  if (v == null) return "—";
  const arred = Math.abs(v) < 0.5 * 10 ** -casas ? 0 : v; // evita exibir "-0,00%"
  return `${arred > 0 ? "+" : ""}${num(casas).format(arred)}%`;
};
export const fmtData = (iso: string) =>
  new Date(iso).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" });

const NOMES_IA: Record<string, string> = { gemini: "Gemini", groq: "Groq", openrouter: "OpenRouter", deepseek: "DeepSeek", anthropic: "Claude" };
export const nomeIA = (p: string | null | undefined) => (p ? (NOMES_IA[p] ?? p) : "IA");
