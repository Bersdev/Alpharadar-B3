"use client";

import { useEffect, useState } from "react";
import { api, fmtBRL, fmtNum, fmtPct, type Overview, type SimulacaoRF } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { FixedIncomeChart } from "@/components/charts";
import { Disclaimer, ErrorState, Loading, PageHeader, Panel } from "@/components/ui";

interface Entrada {
  valor_inicial: number;
  aporte_mensal: number;
  meses: number;
  taxa_lci_pct_cdi: number;
  taxa_lca_pct_cdi: number;
  taxa_cdb_pct_cdi: number;
  dy_pct: number;
}

const INICIAL: Entrada = {
  valor_inicial: 10000,
  aporte_mensal: 500,
  meses: 24,
  taxa_lci_pct_cdi: 92,
  taxa_lca_pct_cdi: 90,
  taxa_cdb_pct_cdi: 105,
  dy_pct: 11,
};

export default function RendaFixaPage() {
  const [e, setE] = useState<Entrada>(INICIAL);
  const [res, setRes] = useState<SimulacaoRF | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [tentativa, setTentativa] = useState(0);
  const { data: overview } = useApi<Overview>("/api/overview");

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const { dy_pct, ...resto } = e;
        setRes(await api<SimulacaoRF>("/api/simulate/fixed-income", { ...resto, dy_dividendos_anual: dy_pct / 100 }));
        setErro(null);
      } catch (err) {
        setErro(err instanceof Error ? err.message : String(err));
      }
    }, 300);
    return () => clearTimeout(t);
  }, [e, tentativa]);

  const set = (campo: keyof Entrada) => (v: number) => setE((x) => ({ ...x, [campo]: v }));

  return (
    <>
      <PageHeader
        title="LCI, LCA, CDB ou dividendos?"
        description="Compare quanto sobra no bolso depois do Imposto de Renda. LCI e LCA são isentas para pessoa física; CDB e Tesouro pagam IR regressivo de 22,5% a 15%."
        aside={overview && (
          <div className="text-right text-sm text-muted">
            CDI hoje: <span className="font-semibold text-text">{fmtPct(overview.macro.cdi_anual, 2)}</span>
            <br />
            Selic: <span className="font-semibold text-text">{fmtPct(overview.macro.selic_anual, 2)}</span>
          </div>
        )}
      />

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Panel title="Sua aplicação" className="h-fit">
          <div className="flex flex-col gap-4">
            <CampoNumero rotulo="Valor inicial (R$)" valor={e.valor_inicial} onChange={set("valor_inicial")} step={1000} />
            <CampoNumero rotulo="Aporte mensal (R$)" valor={e.aporte_mensal} onChange={set("aporte_mensal")} step={100} />
            <Faixa rotulo="Prazo" valor={e.meses} min={3} max={120} step={1} exib={`${e.meses} meses`} onChange={set("meses")} />
            <Faixa rotulo="LCI" valor={e.taxa_lci_pct_cdi} min={70} max={110} step={1} exib={`${e.taxa_lci_pct_cdi}% do CDI`} onChange={set("taxa_lci_pct_cdi")} />
            <Faixa rotulo="LCA" valor={e.taxa_lca_pct_cdi} min={70} max={110} step={1} exib={`${e.taxa_lca_pct_cdi}% do CDI`} onChange={set("taxa_lca_pct_cdi")} />
            <Faixa rotulo="CDB" valor={e.taxa_cdb_pct_cdi} min={80} max={130} step={1} exib={`${e.taxa_cdb_pct_cdi}% do CDI`} onChange={set("taxa_cdb_pct_cdi")} />
            <Faixa rotulo="Dividend yield (FII/ações)" valor={e.dy_pct} min={4} max={16} step={0.5} exib={fmtPct(e.dy_pct)} onChange={set("dy_pct")} />
          </div>
        </Panel>

        <div className="flex min-w-0 flex-col gap-6">
          {erro && <ErrorState message={erro} onRetry={() => setTentativa((n) => n + 1)} />}
          {!res && !erro && <Loading label="Simulando no Python" />}
          {res && <Resultado r={res} e={e} />}
        </div>
      </div>
      <Disclaimer />
    </>
  );
}

function Resultado({ r, e }: { r: SimulacaoRF; e: Entrada }) {
  const ordenados = [...r.produtos].sort((a, b) => b.valor_final_liquido - a.valor_final_liquido);
  const g = r.gross_up;
  return (
    <>
      <Panel title={`Resultado líquido em ${e.meses} meses`}>
        <p className="mb-4 text-sm text-muted">
          Total aplicado: <span className="font-semibold text-text">{fmtBRL(r.total_investido)}</span>. Alíquota de IR para{" "}
          {r.prazo_dias} dias: <span className="font-semibold text-text">{fmtPct(r.aliquota_ir_prazo * 100)}</span>.
        </p>
        <div className="scroll-thin overflow-x-auto">
          <table className="w-full min-w-[520px] text-sm">
            <thead className="text-left text-xs text-muted">
              <tr className="border-b border-line">
                <th className="py-2 font-normal">Produto</th>
                <th className="py-2 font-normal">Taxa</th>
                <th className="py-2 text-right font-normal">Valor líquido</th>
                <th className="py-2 text-right font-normal">Lucro líquido</th>
                <th className="py-2 text-right font-normal">Rentab.</th>
              </tr>
            </thead>
            <tbody>
              {ordenados.map((p, i) => (
                <tr key={p.produto} className={`border-b border-line/60 last:border-0 ${i === 0 ? "text-brand" : ""}`}>
                  <td className="py-2.5 font-semibold">
                    {p.produto}
                    {p.isento_ir && <span className="ml-2 rounded bg-up/10 px-1.5 py-0.5 text-[11px] font-normal text-up">isento de IR</span>}
                  </td>
                  <td className="py-2.5 text-muted">{p.taxa}</td>
                  <td className="py-2.5 text-right font-semibold">{fmtBRL(p.valor_final_liquido)}</td>
                  <td className="py-2.5 text-right">{fmtBRL(p.lucro_liquido)}</td>
                  <td className="py-2.5 text-right">{fmtPct(p.rentabilidade_pct, 2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      <div className="grid gap-6 md:grid-cols-2">
        <Panel title="Gross-up: o CDB que empata com a isenção">
          <p className="wide text-3xl font-semibold text-brand">{fmtNum(g.lci_cdb_equivalente_pct_cdi, 1)}% do CDI</p>
          <p className="mt-2 text-sm leading-relaxed text-muted">{g.explicacao}</p>
          <p className="mt-3 border-t border-line pt-3 text-sm">
            Taxa CDB equivalente = taxa LCI ÷ (1 − alíquota de IR) = {e.taxa_lci_pct_cdi} ÷ (1 − {fmtNum(r.aliquota_ir_prazo, 3)})
          </p>
          <p className="mt-2 text-sm text-muted">
            LCA a {e.taxa_lca_pct_cdi}% equivale a CDB de {fmtNum(g.lca_cdb_equivalente_pct_cdi, 1)}%. O seu CDB de {e.taxa_cdb_pct_cdi}%
            equivale a uma LCI de {fmtNum(g.cdb_lci_equivalente_pct_cdi, 1)}%.
          </p>
        </Panel>
        <Panel title="Imposto que a LCI deixa de pagar">
          <p className="wide text-3xl font-semibold text-up">{fmtBRL(r.economia_ir_lci)}</p>
          <p className="mt-2 text-sm leading-relaxed text-muted">
            É a diferença entre a LCI e um CDB hipotético com a mesma taxa bruta ({e.taxa_lci_pct_cdi}% do CDI) que pagasse IR. Melhor
            opção líquida neste cenário: <span className="font-semibold text-text">{r.melhor_opcao}</span>.
          </p>
        </Panel>
      </div>

      <Panel title="Evolução do patrimônio mês a mês">
        <FixedIncomeChart curva={r.curva_mensal} />
        <p className="mt-2 text-xs text-muted">
          Valores líquidos considerando resgate no mês indicado. Premissas: CDI e Selic constantes, IOF ignorado, custódia do Tesouro de
          0,20% a.a., dividendos reinvestidos com cota estável.
        </p>
      </Panel>
    </>
  );
}

function CampoNumero({ rotulo, valor, onChange, step }: { rotulo: string; valor: number; onChange: (v: number) => void; step: number }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block">{rotulo}</span>
      <input
        type="number"
        min={0}
        step={step}
        value={valor}
        onChange={(ev) => onChange(Math.max(0, Number(ev.target.value) || 0))}
        className="w-full rounded-md border border-line bg-bg px-3 py-2 text-text"
      />
    </label>
  );
}

function Faixa(props: { rotulo: string; valor: number; min: number; max: number; step: number; exib: string; onChange: (v: number) => void }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 flex justify-between">
        {props.rotulo} <span className="font-semibold text-brand">{props.exib}</span>
      </span>
      <input
        type="range"
        className="w-full"
        min={props.min}
        max={props.max}
        step={props.step}
        value={props.valor}
        onChange={(ev) => props.onChange(Number(ev.target.value))}
      />
    </label>
  );
}
