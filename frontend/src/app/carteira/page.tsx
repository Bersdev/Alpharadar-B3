"use client";

import Link from "next/link";
import { useMemo, useState, type FormEvent } from "react";
import { Plus, Trash2 } from "lucide-react";
import { fmtBRL, fmtNum, fmtPct, fmtPreco, fmtSinal, type AtivoAvaliado, type ListaAtivos } from "@/lib/api";
import { LIMITE_MAXIMO, salvarCarteira, useCarteira } from "@/lib/storage";
import { useApi } from "@/lib/useApi";
import { RoscaChart, coresRosca } from "@/components/charts";
import { Delta, Disclaimer, ErrorState, Loading, PageHeader, Panel } from "@/components/ui";

const IR_DIVIDENDOS_EUA = 0.3;

/** Quantos reais vale 1 unidade da moeda do ativo (1 para a B3; câmbio do dia para os EUA). */
const fatorBRL = (a: AtivoAvaliado) => (a.moeda === "USD" && a.cotacao_brl ? a.cotacao_brl / a.cotacao : 1);

export default function CarteiraPage() {
  const { data, error, loading, reload } = useApi<ListaAtivos>("/api/assets");
  const posicoes = useCarteira();
  const [ticker, setTicker] = useState("");
  const [qtd, setQtd] = useState("");
  const [pm, setPm] = useState("");

  const mapa = useMemo(() => new Map((data?.ativos ?? []).map((a) => [a.ticker, a])), [data]);
  const ordenados = useMemo(() => [...(data?.ativos ?? [])].sort((a, b) => a.ticker.localeCompare(b.ticker)), [data]);

  const linhas = useMemo(
    () =>
      posicoes.flatMap((p) => {
        const a = mapa.get(p.ticker);
        if (!a) return [];
        const f = fatorBRL(a);
        const valor = p.qtd * a.cotacao * f;
        const custo = p.qtd * p.pm * f;
        const dividendos = p.qtd * a.dpa_projetado * f * (a.mercado === "EUA" ? 1 - IR_DIVIDENDOS_EUA : 1);
        return [{ p, a, valor, custo, resultado: valor - custo, dividendos }];
      }),
    [posicoes, mapa],
  );

  const total = linhas.reduce((s, l) => s + l.valor, 0);
  const custoTotal = linhas.reduce((s, l) => s + l.custo, 0);
  const dividendosAno = linhas.reduce((s, l) => s + l.dividendos, 0);
  const porSetor = Object.entries(
    linhas.reduce<Record<string, number>>((acc, l) => ({ ...acc, [l.a.setor]: (acc[l.a.setor] ?? 0) + l.valor }), {}),
  )
    .map(([nome, valor]) => ({ nome, valor }))
    .sort((x, y) => y.valor - x.valor);

  function adicionar(e: FormEvent) {
    e.preventDefault();
    const q = Number(qtd.replace(",", "."));
    const preco = Number(pm.replace(",", "."));
    if (!ticker || !Number.isFinite(q) || !Number.isFinite(preco) || !(q > 0) || !(preco > 0) || q > LIMITE_MAXIMO || preco > LIMITE_MAXIMO) return;
    const atual = posicoes.find((p) => p.ticker === ticker);
    if (atual) {
      // novo preço médio = média ponderada pelas quantidades
      const novaQtd = atual.qtd + q;
      const novoPm = (atual.qtd * atual.pm + q * preco) / novaQtd;
      salvarCarteira(posicoes.map((p) => (p.ticker === ticker ? { ticker, qtd: novaQtd, pm: novoPm } : p)));
    } else {
      salvarCarteira([...posicoes, { ticker, qtd: q, pm: preco }]);
    }
    setQtd("");
    setPm("");
  }

  const selecionado = mapa.get(ticker);

  return (
    <>
      <PageHeader
        icon="money-bag"
        title="Minha carteira"
        description="Acompanhe o valor, o resultado e os dividendos projetados dos seus ativos. Os dados ficam só no seu navegador."
      />
      {loading && !data && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <div className="grid gap-4 xl:grid-cols-3">
          <Panel title="Adicionar ativo" className="xl:col-span-1">
            <form onSubmit={adicionar} className="flex flex-col gap-3 text-sm">
              <label>
                <span className="mb-1 block text-muted">Ativo</span>
                <select value={ticker} onChange={(e) => setTicker(e.target.value)} className="w-full rounded-xl border border-line bg-raised px-3 py-2 text-text" required>
                  <option value="">Escolha um ativo</option>
                  {ordenados.map((a) => <option key={a.ticker} value={a.ticker}>{a.ticker}, {a.nome}</option>)}
                </select>
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label>
                  <span className="mb-1 block text-muted">Quantidade</span>
                  <input inputMode="decimal" value={qtd} onChange={(e) => setQtd(e.target.value)} placeholder="100" className="w-full rounded-xl border border-line bg-raised px-3 py-2 text-text" required />
                </label>
                <label>
                  <span className="mb-1 block text-muted">Preço médio{selecionado ? ` (${selecionado.moeda === "USD" ? "US$" : "R$"})` : ""}</span>
                  <input inputMode="decimal" value={pm} onChange={(e) => setPm(e.target.value)} placeholder={selecionado ? fmtNum(selecionado.cotacao) : "0,00"} className="w-full rounded-xl border border-line bg-raised px-3 py-2 text-text" required />
                </label>
              </div>
              <button type="submit" className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-4 py-2.5 font-medium text-white hover:brightness-110">
                <Plus size={16} /> Adicionar à carteira
              </button>
              <p className="text-xs leading-relaxed text-muted">
                Comprando de novo o mesmo ativo, o preço médio é recalculado pela média ponderada. Para ações dos EUA, informe o preço em dólar; os totais são convertidos pelo câmbio do dia.
              </p>
            </form>
          </Panel>

          <Panel title="Resumo" className="xl:col-span-2">
            {linhas.length === 0 ? (
              <p className="py-10 text-center text-muted">Sua carteira está vazia. Adicione o primeiro ativo ao lado para ver o resumo.</p>
            ) : (
              <div className="grid gap-6 md:grid-cols-[1.2fr_1fr] md:items-center">
                <dl className="grid grid-cols-2 gap-x-6 gap-y-5">
                  <Metrica rotulo="Patrimônio atual" valor={fmtBRL(total)} grande />
                  <Metrica rotulo="Resultado" valor={<><span className={total - custoTotal >= 0 ? "text-up" : "text-down"}>{fmtBRL(total - custoTotal)}</span> <span className="text-sm font-normal"><Delta value={custoTotal ? ((total - custoTotal) / custoTotal) * 100 : 0} /></span></>} grande />
                  <Metrica rotulo="Dividendos projetados (12 meses)" valor={fmtBRL(dividendosAno)} />
                  <Metrica rotulo="Dividend yield da carteira" valor={fmtPct(total ? (dividendosAno / total) * 100 : 0)} />
                </dl>
                <div>
                  <RoscaChart dados={porSetor} />
                </div>
              </div>
            )}
            {linhas.length > 0 && (
              <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
                {porSetor.map((s, i) => (
                  <li key={s.nome} className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full" style={{ background: coresRosca(i) }} /> {s.nome} {fmtPct((s.valor / total) * 100, 0)}
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          {linhas.length > 0 && (
            <div className="card scroll-thin overflow-x-auto xl:col-span-3">
              <table className="w-full min-w-[860px] text-sm">
                <thead className="text-left text-xs text-muted">
                  <tr className="border-b border-line">
                    <th className="px-4 py-3 font-normal">Ativo</th>
                    <th className="px-4 py-3 text-right font-normal">Qtd.</th>
                    <th className="px-4 py-3 text-right font-normal">Preço médio</th>
                    <th className="px-4 py-3 text-right font-normal">Cotação</th>
                    <th className="px-4 py-3 text-right font-normal">Valor atual</th>
                    <th className="px-4 py-3 text-right font-normal">Resultado</th>
                    <th className="px-4 py-3 text-right font-normal">Peso</th>
                    <th className="px-4 py-3 text-right font-normal">Dividendos/ano</th>
                    <th className="w-10 px-3 py-3" />
                  </tr>
                </thead>
                <tbody>
                  {linhas.map(({ p, a, valor, custo, resultado, dividendos }) => (
                    <tr key={p.ticker} className="border-b border-line/60 last:border-0 hover:bg-raised/50">
                      <td className="px-4 py-3">
                        <Link href={`/ativo/${a.ticker}`} className="font-semibold hover:text-brand">{a.ticker}</Link>
                        <div className="text-xs text-muted">{a.setor}</div>
                      </td>
                      <td className="px-4 py-3 text-right">{fmtNum(p.qtd, p.qtd % 1 ? 2 : 0)}</td>
                      <td className="px-4 py-3 text-right text-muted">{fmtPreco(p.pm, a.moeda)}</td>
                      <td className="px-4 py-3 text-right">{fmtPreco(a.cotacao, a.moeda)}</td>
                      <td className="px-4 py-3 text-right font-medium">{fmtBRL(valor)}</td>
                      <td className="px-4 py-3 text-right">
                        <span className={resultado >= 0 ? "text-up" : "text-down"}>{fmtBRL(resultado)}</span>
                        <div className="text-xs">{fmtSinal(custo ? (resultado / custo) * 100 : 0)}</div>
                      </td>
                      <td className="px-4 py-3 text-right text-muted">{fmtPct(total ? (valor / total) * 100 : 0)}</td>
                      <td className="px-4 py-3 text-right">{fmtBRL(dividendos)}</td>
                      <td className="px-3 py-3">
                        <button onClick={() => salvarCarteira(posicoes.filter((x) => x.ticker !== p.ticker))} aria-label={`Remover ${p.ticker} da carteira`} className="grid h-7 w-7 place-items-center rounded-lg text-muted hover:bg-raised hover:text-down">
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
      <Disclaimer />
    </>
  );
}

function Metrica({ rotulo, valor, grande }: { rotulo: string; valor: React.ReactNode; grande?: boolean }) {
  return (
    <div>
      <dt className="text-sm text-muted">{rotulo}</dt>
      <dd className={`wide mt-0.5 font-semibold ${grande ? "text-2xl" : "text-lg"}`}>{valor}</dd>
    </div>
  );
}
