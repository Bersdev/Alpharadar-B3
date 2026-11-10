"use client";

// Gráficos (Recharts) usados nas páginas de ativo e renda fixa.
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtBRL, fmtData, fmtPreco, type Pilar, type SimulacaoRF } from "@/lib/api";

const eixo = { stroke: "var(--muted)", fontSize: 11, tickLine: false, axisLine: false } as const;
const tooltipStyle = {
  contentStyle: { background: "var(--raised)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 12 },
  labelStyle: { color: "var(--muted)" },
  itemStyle: { color: "var(--text)" },
};

export function PriceChart({ dados, moeda = "BRL" }: { dados: { data: string; fechamento: number }[]; moeda?: string }) {
  const subiu = dados.length > 1 && dados[dados.length - 1].fechamento >= dados[0].fechamento;
  const cor = subiu ? "var(--up)" : "var(--down)";
  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={dados} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="precoFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={cor} stopOpacity={0.25} />
            <stop offset="100%" stopColor={cor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="data" {...eixo} tickFormatter={fmtData} minTickGap={40} />
        <YAxis {...eixo} domain={["auto", "auto"]} width={52} tickFormatter={(v: number) => v.toFixed(0)} />
        <Tooltip {...tooltipStyle} labelFormatter={(l) => new Date(String(l)).toLocaleDateString("pt-BR")} formatter={(v) => [fmtPreco(Number(v), moeda), "Fechamento"]} />
        <Area type="monotone" dataKey="fechamento" stroke={cor} strokeWidth={1.8} fill="url(#precoFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function DividendChart({ dados, moeda = "BRL" }: { dados: { data: string; valor: number }[]; moeda?: string }) {
  return (
    <ResponsiveContainer width="100%" height={150}>
      <BarChart data={dados} margin={{ left: 0, right: 8, top: 4, bottom: 0 }}>
        <XAxis dataKey="data" {...eixo} tickFormatter={(d: string) => new Date(d).toLocaleDateString("pt-BR", { month: "short", year: "2-digit" })} minTickGap={24} />
        <YAxis {...eixo} width={52} tickFormatter={(v: number) => v.toFixed(2)} />
        <Tooltip {...tooltipStyle} cursor={{ fill: "var(--raised)" }} labelFormatter={(l) => new Date(String(l)).toLocaleDateString("pt-BR")} formatter={(v) => [fmtPreco(Number(v), moeda), "Provento"]} />
        <Bar dataKey="valor" fill="var(--brand)" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** O Score Alpha desenhado como uma tela de radar: cada eixo é um pilar de 0 a 20. */
export function ScoreRadar({ pilares }: { pilares: Pilar[] }) {
  const curto: Record<string, string> = {
    "Margem vs. Preço-Teto": "Margem",
    "Dividend Yield Projetado": "Dividendos",
    "Rentabilidade (ROE)": "Rentabilidade",
    "Sentimento de Notícias": "Notícias",
  };
  const dados = pilares.map((p) => ({ pilar: curto[p.nome] ?? p.nome, pontos: Number(p.pontos.toFixed(1)) }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <RadarChart data={dados} outerRadius="72%">
        <PolarGrid stroke="var(--line)" />
        <PolarAngleAxis dataKey="pilar" tick={{ fill: "var(--muted)", fontSize: 11 }} />
        <PolarRadiusAxis domain={[0, 20]} tick={false} axisLine={false} />
        <Tooltip {...tooltipStyle} formatter={(v) => [`${v} de 20`, "Pontos"]} />
        <Radar dataKey="pontos" stroke="var(--brand)" fill="var(--brand)" fillOpacity={0.25} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

const SERIES_RF = [
  { chave: "lci", nome: "LCI", cor: "var(--brand)" },
  { chave: "lca", nome: "LCA", cor: "#8fb0ff" },
  { chave: "cdb_liquido", nome: "CDB (líquido)", cor: "#6fa8dc" },
  { chave: "tesouro_selic_liquido", nome: "Tesouro Selic (líquido)", cor: "#a58bd8" },
  { chave: "dividendos_reinvestidos", nome: "Dividendos reinvestidos", cor: "var(--up)" },
  { chave: "investido", nome: "Total investido", cor: "var(--muted)" },
] as const;

export function FixedIncomeChart({ curva }: { curva: SimulacaoRF["curva_mensal"] }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={curva} margin={{ left: 8, right: 8, top: 8, bottom: 0 }}>
        <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="mes" {...eixo} tickFormatter={(m: number) => `${m}m`} minTickGap={24} />
        <YAxis {...eixo} width={70} domain={["auto", "auto"]} tickFormatter={(v: number) => `R$ ${(v / 1000).toFixed(0)} mil`} />
        <Tooltip {...tooltipStyle} labelFormatter={(m) => `Mês ${m}`} formatter={(v, nome) => [fmtBRL(Number(v)), nome]} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--muted)" }} />
        {SERIES_RF.map((s) => (
          <Line
            key={s.chave}
            type="monotone"
            dataKey={s.chave}
            name={s.nome}
            stroke={s.cor}
            strokeWidth={s.chave === "lci" ? 2.4 : 1.6}
            strokeDasharray={s.chave === "investido" ? "4 4" : undefined}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/** Ibovespa (base 100) e juro de 10 anos dos EUA: a relação inversa clássica entre juros e bolsa. */
export function JurosBolsaChart({ dados }: { dados: { data: string; ibovespa: number; juro_10a_eua: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={dados} margin={{ left: 0, right: 0, top: 8, bottom: 0 }}>
        <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
        <XAxis dataKey="data" {...eixo} tickFormatter={fmtData} minTickGap={50} />
        <YAxis yAxisId="ibov" {...eixo} width={44} domain={["auto", "auto"]} tickFormatter={(v: number) => v.toFixed(0)} />
        <YAxis yAxisId="juro" orientation="right" {...eixo} width={44} domain={["auto", "auto"]} tickFormatter={(v: number) => `${v.toFixed(1)}%`} />
        <Tooltip {...tooltipStyle} labelFormatter={(l) => new Date(String(l)).toLocaleDateString("pt-BR")}
          formatter={(v, nome) => [nome === "Ibovespa (base 100)" ? Number(v).toFixed(1) : `${Number(v).toFixed(2)}%`, nome]} />
        <Legend wrapperStyle={{ fontSize: 12, color: "var(--muted)" }} />
        <Line yAxisId="ibov" type="monotone" dataKey="ibovespa" name="Ibovespa (base 100)" stroke="var(--brand)" strokeWidth={2} dot={false} />
        <Line yAxisId="juro" type="monotone" dataKey="juro_10a_eua" name="Juro de 10 anos dos EUA" stroke="var(--warn)" strokeWidth={2} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

const CORES_ROSCA = ["var(--brand)", "var(--up)", "var(--warn)", "#8b5cf6", "#06b6d4", "var(--down)", "#ec4899", "#84cc16", "var(--muted)"];

/** Rosca de distribuição da carteira (por setor ou mercado). */
export function RoscaChart({ dados }: { dados: { nome: string; valor: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={dados} dataKey="valor" nameKey="nome" innerRadius={55} outerRadius={85} paddingAngle={2} stroke="none">
          {dados.map((_, i) => (
            <Cell key={i} fill={CORES_ROSCA[i % CORES_ROSCA.length]} />
          ))}
        </Pie>
        <Tooltip {...tooltipStyle} formatter={(v, nome) => [fmtBRL(Number(v)), nome]} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export const coresRosca = (i: number) => CORES_ROSCA[i % CORES_ROSCA.length];
