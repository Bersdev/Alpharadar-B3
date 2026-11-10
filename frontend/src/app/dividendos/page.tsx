"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { fmtBRL, fmtPct, fmtPreco, type ListaAtivos } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Disclaimer, ErrorState, InfoTip, Loading, MargemBadge, PageHeader, Panel, StarButton } from "@/components/ui";

const IR_DIVIDENDOS_EUA = 0.3; // retenção na fonte para brasileiros

type FiltroMercado = "todos" | "B3" | "EUA";
type FiltroTipo = "todos" | "acao" | "fii";

export default function DividendosPage() {
  const { data, error, loading, reload } = useApi<ListaAtivos>("/api/assets");
  const [mercado, setMercado] = useState<FiltroMercado>("todos");
  const [tipo, setTipo] = useState<FiltroTipo>("todos");
  const [valor, setValor] = useState(10000);
  const [meta, setMeta] = useState(1000);

  const linhas = useMemo(() => {
    if (!data) return [];
    return data.ativos
      .filter((a) => a.dy_projetado > 0 && (mercado === "todos" || a.mercado === mercado) && (tipo === "todos" || a.tipo === tipo))
      .map((a) => {
        const dyLiquido = a.mercado === "EUA" ? a.dy_projetado * (1 - IR_DIVIDENDOS_EUA) : a.dy_projetado;
        const precoBRL = a.moeda === "USD" ? (a.cotacao_brl ?? a.cotacao * 5.5) : a.cotacao;
        return { a, dyLiquido, renda: (valor * dyLiquido) / 100, cotas: Math.floor(valor / precoBRL) };
      })
      .sort((x, y) => y.dyLiquido - x.dyLiquido);
  }, [data, mercado, tipo, valor]);

  const top = linhas.slice(0, 10);
  const dyMedio = top.length ? top.reduce((s, l) => s + l.dyLiquido, 0) / top.length : 0;
  const capitalNecessario = dyMedio > 0 ? (meta * 12) / (dyMedio / 100) : 0;
  const rendaMensalComValor = (valor * dyMedio) / 100 / 12;

  return (
    <>
      <PageHeader
        icon="money-bag"
        title="Dividendos e renda passiva"
        description="Quanto cada ativo deve pagar nos próximos 12 meses e quanto você precisaria investir para viver de renda."
      />

      <div className="mb-4 grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <Panel title="Calculadora de renda passiva">
          <div className="grid gap-4 sm:grid-cols-2">
            <Campo rotulo="Quanto quer investir (R$)" valor={valor} onChange={setValor} passo={1000} />
            <Campo rotulo="Renda mensal desejada (R$)" valor={meta} onChange={setMeta} passo={100} />
          </div>
          <dl className="mt-5 grid gap-4 border-t border-line pt-4 sm:grid-cols-2">
            <div>
              <dt className="text-sm text-muted">Com os 10 maiores pagadores ({fmtPct(dyMedio, 1)} ao ano)</dt>
              <dd className="wide mt-1 text-2xl font-semibold">{fmtBRL(rendaMensalComValor)} <span className="text-sm font-normal text-muted">por mês</span></dd>
            </div>
            <div>
              <dt className="text-sm text-muted">Para receber {fmtBRL(meta)} por mês, precisaria de</dt>
              <dd className="wide mt-1 text-2xl font-semibold text-brand">{capitalNecessario ? fmtBRL(capitalNecessario) : "—"}</dd>
            </div>
          </dl>
          <p className="mt-4 text-xs leading-relaxed text-muted">
            Dividendos são estimativas e podem ser reduzidos ou suspensos. Concentrar tudo nos maiores yields costuma significar mais risco: um yield muito alto
            às vezes é só o preço em queda. Ações dos EUA já aparecem líquidas dos 30% de IR retido na fonte.
          </p>
        </Panel>

        <Panel title="Como o AlphaRadar estima o dividendo do ano">
          <ol className="space-y-2 text-sm leading-relaxed text-muted">
            <li><strong className="text-text">1.</strong> Parte do lucro por ação (LPA) dos últimos 12 meses <InfoTip termo="lpa" />.</li>
            <li><strong className="text-text">2.</strong> Aplica o crescimento esperado do lucro (limitado entre -10% e +20%).</li>
            <li><strong className="text-text">3.</strong> Multiplica pelo payout, a parte do lucro que a empresa costuma distribuir <InfoTip termo="payout" />.</li>
            <li><strong className="text-text">4.</strong> Divide pela cotação para chegar ao dividend yield projetado <InfoTip termo="dividend_yield" />.</li>
          </ol>
          <p className="mt-3 text-xs text-muted">FIIs: o payout é fixado em 95% do resultado, e os rendimentos mensais costumam ser isentos de IR para pessoa física <InfoTip termo="fii" />.</p>
        </Panel>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-3">
        <Seletor valor={mercado} onChange={(v) => setMercado(v as FiltroMercado)} opcoes={[["todos", "Todos"], ["B3", "B3"], ["EUA", "EUA"]]} rotulo="Mercado" />
        <Seletor valor={tipo} onChange={(v) => setTipo(v as FiltroTipo)} opcoes={[["todos", "Ações e FIIs"], ["acao", "Ações"], ["fii", "FIIs"]]} rotulo="Tipo" />
        <span className="text-xs text-muted">{linhas.length} ativos pagam dividendos</span>
      </div>

      {loading && !data && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <div className="card scroll-thin overflow-x-auto">
          <table className="w-full min-w-[820px] text-sm">
            <thead className="text-left text-xs text-muted">
              <tr className="border-b border-line">
                <th className="w-10 px-3 py-3" />
                <th className="px-2 py-3 font-normal">Ativo</th>
                <th className="px-4 py-3 text-right font-normal">DY atual</th>
                <th className="px-4 py-3 text-right font-normal">DY projetado</th>
                <th className="px-4 py-3 text-right font-normal">Dividendo por {`ação/cota`}</th>
                <th className="px-4 py-3 text-right font-normal">Renda anual com {fmtBRL(valor)}</th>
                <th className="px-4 py-3 text-right font-normal">Preço-teto</th>
              </tr>
            </thead>
            <tbody>
              {linhas.map(({ a, dyLiquido, renda }) => (
                <tr key={a.ticker} className="border-b border-line/60 last:border-0 hover:bg-raised/50">
                  <td className="px-3 py-3"><StarButton ticker={a.ticker} /></td>
                  <td className="px-2 py-3">
                    <Link href={`/ativo/${a.ticker}`} className="font-semibold hover:text-brand">{a.ticker}</Link>
                    <div className="text-xs text-muted">{a.nome}</div>
                  </td>
                  <td className="px-4 py-3 text-right text-muted">{fmtPct(a.dy_atual)}</td>
                  <td className="px-4 py-3 text-right">
                    <span className="font-semibold">{fmtPct(dyLiquido)}</span>
                    {a.mercado === "EUA" && <span className="block text-[11px] text-muted">líquido de IR</span>}
                  </td>
                  <td className="px-4 py-3 text-right">{fmtPreco(a.dpa_projetado, a.moeda)}</td>
                  <td className="px-4 py-3 text-right font-medium">{fmtBRL(renda)}</td>
                  <td className="px-4 py-3 text-right"><MargemBadge margem={a.margem_projetiva} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Disclaimer />
    </>
  );
}

function Campo({ rotulo, valor, onChange, passo }: { rotulo: string; valor: number; onChange: (v: number) => void; passo: number }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block text-muted">{rotulo}</span>
      <input
        type="number"
        min={0}
        step={passo}
        value={valor}
        onChange={(e) => onChange(Math.max(0, Number(e.target.value) || 0))}
        className="w-full rounded-xl border border-line bg-raised px-3 py-2 text-text"
      />
    </label>
  );
}

function Seletor({ valor, onChange, opcoes, rotulo }: { valor: string; onChange: (v: string) => void; opcoes: [string, string][]; rotulo: string }) {
  return (
    <div className="inline-flex rounded-xl border border-line bg-surface p-0.5 text-sm" role="tablist" aria-label={rotulo}>
      {opcoes.map(([v, nome]) => (
        <button key={v} role="tab" aria-selected={valor === v} onClick={() => onChange(v)}
          className={`rounded-lg px-3 py-1.5 ${valor === v ? "bg-raised font-medium text-text" : "text-muted hover:text-text"}`}>
          {nome}
        </button>
      ))}
    </div>
  );
}
