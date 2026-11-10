"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowDownUp, RotateCcw } from "lucide-react";
import { api, fmtBRL, fmtPct, type AtivoAvaliado } from "@/lib/api";
import { Disclaimer, ErrorState, Loading, PageHeader, Panel, ScorePill } from "@/components/ui";

type Ordem = "score" | "margem_projetiva" | "dy_projetado" | "ticker";
type Filtro = "todos" | "acao" | "fii";

export default function PrecoTetoPage() {
  const [yieldPct, setYieldPct] = useState<number | null>(null); // null = padrão 6% ações / 8% FIIs
  const [crescPct, setCrescPct] = useState<number | null>(null); // null = crescimento de cada empresa
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [ordem, setOrdem] = useState<Ordem>("score");
  const [dados, setDados] = useState<AtivoAvaliado[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [tentativa, setTentativa] = useState(0);

  // Cada mudança nos sliders dispara o cálculo no backend Python (com 250 ms de espera).
  useEffect(() => {
    const t = setTimeout(async () => {
      setCalculando(true);
      try {
        const r = await api<{ resultados: AtivoAvaliado[] }>("/api/simulate/valuation", {
          yield_desejado: yieldPct == null ? null : yieldPct / 100,
          crescimento_g: crescPct == null ? null : crescPct / 100,
        });
        setDados(r.resultados);
        setErro(null);
      } catch (e) {
        setErro(e instanceof Error ? e.message : String(e));
      } finally {
        setCalculando(false);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [yieldPct, crescPct, tentativa]);

  const linhas = useMemo(() => {
    if (!dados) return [];
    const filtradas = dados.filter((a) => filtro === "todos" || a.tipo === filtro);
    const valor = (a: AtivoAvaliado) =>
      ordem === "score" ? a.score.total : ordem === "ticker" ? 0 : (a[ordem] ?? -Infinity);
    return [...filtradas].sort((a, b) => (ordem === "ticker" ? a.ticker.localeCompare(b.ticker) : valor(b) - valor(a)));
  }, [dados, filtro, ordem]);

  return (
    <>
      <PageHeader
        title="Laboratório de preço-teto"
        description="Defina quanto de dividendo você exige e quanto espera de crescimento. O motor Python recalcula Bazin, preço-teto projetivo, Graham e o Score Alpha de todos os ativos."
      />

      <Panel className="mb-6">
        <div className="grid gap-6 md:grid-cols-[1fr_1fr_auto] md:items-end">
          <Slider
            label="Dividend yield que você exige"
            valor={yieldPct ?? 6}
            exibicao={yieldPct == null ? "6% ações, 8% FIIs" : `${yieldPct.toFixed(1).replace(".", ",")}% ao ano`}
            min={5}
            max={12}
            step={0.5}
            onChange={setYieldPct}
            dica="Quanto maior a exigência, menor o preço-teto."
          />
          <Slider
            label="Crescimento projetado do lucro"
            valor={crescPct ?? 0}
            exibicao={crescPct == null ? "o de cada empresa" : `${crescPct > 0 ? "+" : ""}${crescPct}% em 12 meses`}
            min={-10}
            max={20}
            step={1}
            onChange={setCrescPct}
            dica="Aplicado ao LPA atual para projetar os dividendos."
          />
          <button
            onClick={() => {
              setYieldPct(null);
              setCrescPct(null);
            }}
            disabled={yieldPct == null && crescPct == null}
            className="inline-flex items-center gap-2 rounded-md border border-line px-3 py-2 text-sm text-muted hover:bg-raised hover:text-text disabled:opacity-40"
          >
            <RotateCcw size={14} /> Premissas padrão
          </button>
        </div>
        <p className="mt-5 border-t border-line pt-4 text-[13px] leading-relaxed text-muted">
          Preço-teto projetivo = LPA × (1 + crescimento) × payout ÷ yield exigido. Bazin usa os dividendos pagos nos
          últimos 12 meses; Graham = √(22,5 × LPA × VPA).
        </p>
      </Panel>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-line p-0.5 text-sm" role="tablist">
          {(["todos", "acao", "fii"] as Filtro[]).map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={filtro === f}
              onClick={() => setFiltro(f)}
              className={`rounded-md px-3 py-1.5 ${filtro === f ? "bg-raised text-text" : "text-muted hover:text-text"}`}
            >
              {f === "todos" ? "Todos" : f === "acao" ? "Ações" : "FIIs"}
            </button>
          ))}
        </div>
        <span className="text-xs text-muted" aria-live="polite">
          {calculando ? "Recalculando no Python…" : dados ? `${linhas.length} ativos` : ""}
        </span>
      </div>

      {erro && <ErrorState message={erro} onRetry={() => setTentativa((n) => n + 1)} />}
      {!dados && !erro && <Loading />}
      {dados && (
        <div className="scroll-thin overflow-x-auto rounded-2xl border border-line bg-surface">
          <table className="w-full min-w-[920px] text-sm">
            <thead className="text-left text-xs text-muted">
              <tr className="border-b border-line">
                <Th onClick={() => setOrdem("ticker")} ativo={ordem === "ticker"}>Ativo</Th>
                <th className="px-4 py-3 text-right font-normal">Cotação</th>
                <th className="px-4 py-3 text-right font-normal">Teto Bazin</th>
                <th className="px-4 py-3 text-right font-normal">Teto projetivo</th>
                <th className="px-4 py-3 text-right font-normal">Graham</th>
                <Th onClick={() => setOrdem("margem_projetiva")} ativo={ordem === "margem_projetiva"} direita>
                  Margem de segurança
                </Th>
                <Th onClick={() => setOrdem("dy_projetado")} ativo={ordem === "dy_projetado"} direita>
                  Dividendos projetados
                </Th>
                <Th onClick={() => setOrdem("score")} ativo={ordem === "score"} direita>
                  Score Alpha
                </Th>
              </tr>
            </thead>
            <tbody className={calculando ? "opacity-60" : ""}>
              {linhas.map((a) => (
                <tr key={a.ticker} className="border-b border-line/60 last:border-0 hover:bg-raised/50">
                  <td className="px-4 py-3">
                    <Link href={`/ativo/${a.ticker}`} className="font-semibold hover:text-brand">
                      {a.ticker}
                    </Link>
                    <div className="text-xs text-muted">{a.setor}</div>
                  </td>
                  <td className="px-4 py-3 text-right">{fmtBRL(a.cotacao)}</td>
                  <td className="px-4 py-3 text-right text-muted">{fmtBRL(a.preco_teto_bazin)}</td>
                  <td className="px-4 py-3 text-right font-medium">{fmtBRL(a.preco_teto_projetivo)}</td>
                  <td className="px-4 py-3 text-right text-muted">{fmtBRL(a.preco_justo_graham)}</td>
                  <td className="px-4 py-3 text-right">
                    <Margem valor={a.margem_projetiva} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    {fmtBRL(a.dpa_projetado)}
                    <div className="text-xs text-muted">{fmtPct(a.dy_projetado)} ao ano</div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <ScorePill total={a.score.total} classificacao={a.score.classificacao} />
                  </td>
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

function Margem({ valor }: { valor: number | null }) {
  if (valor == null) return <span className="text-muted">sem dividendos</span>;
  const largura = Math.min(Math.abs(valor), 60) / 60;
  return (
    <div className="flex items-center justify-end gap-2">
      <div className="hidden h-1.5 w-16 rounded-full bg-raised sm:block">
        <div
          className={`h-1.5 rounded-full ${valor >= 0 ? "bg-up" : "bg-down"}`}
          style={{ width: `${largura * 100}%`, marginLeft: valor >= 0 ? 0 : "auto" }}
        />
      </div>
      <span className={`w-16 font-medium ${valor >= 0 ? "text-up" : "text-down"}`}>
        {valor > 0 ? "+" : ""}
        {fmtPct(valor)}
      </span>
    </div>
  );
}

function Th({
  children,
  onClick,
  ativo,
  direita,
}: {
  children: React.ReactNode;
  onClick: () => void;
  ativo: boolean;
  direita?: boolean;
}) {
  return (
    <th className={`px-4 py-3 font-normal ${direita ? "text-right" : ""}`} aria-sort={ativo ? "descending" : "none"}>
      <button onClick={onClick} className={`inline-flex items-center gap-1 hover:text-text ${ativo ? "text-brand" : ""}`}>
        {children} <ArrowDownUp size={11} />
      </button>
    </th>
  );
}

function Slider(props: {
  label: string;
  valor: number;
  exibicao: string;
  min: number;
  max: number;
  step: number;
  dica: string;
  onChange: (v: number) => void;
}) {
  const id = props.label.replace(/\s/g, "-");
  return (
    <div>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-sm font-medium">
          {props.label}
        </label>
        <span className="wide text-sm font-semibold text-brand">{props.exibicao}</span>
      </div>
      <input
        id={id}
        type="range"
        className="w-full"
        min={props.min}
        max={props.max}
        step={props.step}
        value={props.valor}
        onChange={(e) => props.onChange(Number(e.target.value))}
      />
      <p className="mt-1 text-xs text-muted">{props.dica}</p>
    </div>
  );
}
