"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowDownUp, RotateCcw } from "lucide-react";
import { api, fmtPct, fmtPreco, type AtivoAvaliado } from "@/lib/api";
import type { ChaveTermo } from "@/lib/glossario";
import { useFavoritos } from "@/lib/storage";
import { Disclaimer, ErrorState, InfoTip, Loading, MargemBadge, PageHeader, Panel, ScorePill, StarButton } from "@/components/ui";

type Ordem = "score" | "margem_projetiva" | "dy_projetado" | "ticker";
type Filtro = "todos" | "acao" | "fii" | "eua";

export default function PrecoTetoPage() {
  const [yieldPct, setYieldPct] = useState<number | null>(null); // null = padrão 6% ações / 8% FIIs
  const [crescPct, setCrescPct] = useState<number | null>(null); // null = crescimento de cada empresa
  const [filtro, setFiltro] = useState<Filtro>("todos");
  const [ordem, setOrdem] = useState<Ordem>("score");
  const [dados, setDados] = useState<AtivoAvaliado[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [calculando, setCalculando] = useState(false);
  const [tentativa, setTentativa] = useState(0);
  // Critérios do usuário: reduzem o universo a poucas ideias (a filosofia "menos ruído, mais convicção").
  const [busca, setBusca] = useState("");
  const [soMargem, setSoMargem] = useState(false);
  const [soFavoritos, setSoFavoritos] = useState(false);
  const [dyMin, setDyMin] = useState(0);
  const [roeMin, setRoeMin] = useState(0);
  const [setor, setSetor] = useState("todos");
  const favoritos = useFavoritos();

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
    const q = busca.trim().toLowerCase();
    const filtradas = dados.filter(
      (a) =>
        (filtro === "todos" ? true : filtro === "eua" ? a.mercado === "EUA" : a.tipo === filtro && a.mercado === "B3") &&
        (!q || a.ticker.toLowerCase().includes(q) || a.nome.toLowerCase().includes(q)) &&
        (!soMargem || (a.margem_projetiva ?? -1) > 0) &&
        (!soFavoritos || favoritos.includes(a.ticker)) &&
        (a.dy_projetado ?? 0) >= dyMin &&
        (roeMin === 0 || a.tipo === "fii" || (a.roe ?? 0) >= roeMin) &&
        (setor === "todos" || a.setor === setor),
    );
    const valor = (a: AtivoAvaliado) =>
      ordem === "score" ? a.score.total : ordem === "ticker" ? 0 : (a[ordem] ?? -Infinity);
    return [...filtradas].sort((a, b) => (ordem === "ticker" ? a.ticker.localeCompare(b.ticker) : valor(b) - valor(a)));
  }, [dados, filtro, ordem, busca, soMargem, soFavoritos, dyMin, roeMin, setor, favoritos]);
  const setores = useMemo(() => [...new Set((dados ?? []).map((a) => a.setor))].sort(), [dados]);
  const filtrosAtivos = busca !== "" || soMargem || soFavoritos || dyMin > 0 || roeMin > 0 || setor !== "todos";
  const limparFiltros = () => {
    setBusca("");
    setSoMargem(false);
    setSoFavoritos(false);
    setDyMin(0);
    setRoeMin(0);
    setSetor("todos");
  };

  return (
    <>
      <PageHeader
        icon="scales"
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

      <Panel
        title="Seus critérios"
        className="mb-6"
        action={filtrosAtivos && <button onClick={limparFiltros} className="text-sm font-medium text-brand hover:underline">Limpar critérios</button>}
      >
        <div className="grid gap-x-6 gap-y-5 md:grid-cols-2 xl:grid-cols-4">
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Buscar</span>
            <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Ticker ou nome" className="w-full rounded-xl border border-line bg-raised px-3 py-2 text-text placeholder:text-muted" />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Setor</span>
            <select value={setor} onChange={(e) => setSetor(e.target.value)} className="w-full rounded-xl border border-line bg-raised px-3 py-2 text-text">
              <option value="todos">Todos os setores</option>
              {setores.map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </label>
          <Slider label="Dividend yield projetado mínimo" valor={dyMin} exibicao={dyMin === 0 ? "qualquer" : `${dyMin.toFixed(1).replace(".", ",")}% ou mais`} min={0} max={15} step={0.5} onChange={setDyMin} dica="Descarta quem paga menos que isso." />
          <Slider label="ROE mínimo (empresas)" valor={roeMin} exibicao={roeMin === 0 ? "qualquer" : `${roeMin}% ou mais`} min={0} max={30} step={1} onChange={setRoeMin} dica="Rentabilidade sobre o patrimônio. FIIs não entram neste filtro." />
        </div>
        <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 border-t border-line pt-4 text-sm">
          <label className="flex cursor-pointer items-center gap-2">
            <input type="checkbox" checked={soMargem} onChange={(e) => setSoMargem(e.target.checked)} className="h-4 w-4 accent-[var(--brand)]" />
            Só com margem positiva <InfoTip termo="margem_seguranca" />
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input type="checkbox" checked={soFavoritos} onChange={(e) => setSoFavoritos(e.target.checked)} className="h-4 w-4 accent-[var(--brand)]" />
            Só meus favoritos ({favoritos.length})
          </label>
        </div>
      </Panel>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-line p-0.5 text-sm" role="tablist">
          {(["todos", "acao", "fii", "eua"] as Filtro[]).map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={filtro === f}
              onClick={() => setFiltro(f)}
              className={`rounded-md px-3 py-1.5 ${filtro === f ? "bg-raised text-text" : "text-muted hover:text-text"}`}
            >
              {f === "todos" ? "Todos" : f === "acao" ? "Ações B3" : f === "fii" ? "FIIs" : "Ações EUA"}
            </button>
          ))}
        </div>
        <span className="text-xs text-muted" aria-live="polite">
          {calculando ? "Recalculando no Python…" : dados ? `${linhas.length} de ${dados.length} ativos` : ""}
        </span>
      </div>

      {erro && <ErrorState message={erro} onRetry={() => setTentativa((n) => n + 1)} />}
      {!dados && !erro && <Loading />}
      {dados && linhas.length === 0 && (
        <div className="card py-12 text-center">
          <p className="font-medium">Nenhum ativo atende a todos os critérios.</p>
          <p className="mt-1 text-sm text-muted">Afrouxe o dividend yield ou o ROE mínimo, ou limpe os critérios.</p>
          <button onClick={limparFiltros} className="mt-4 rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white hover:brightness-110">
            Limpar critérios
          </button>
        </div>
      )}
      {dados && linhas.length > 0 && (
        <div className="card scroll-thin overflow-x-auto">
          <table className="w-full min-w-[1000px] text-sm">
            <thead className="text-left text-xs text-muted">
              <tr className="border-b border-line">
                <th className="w-10 px-3 py-3" />
                <Th onClick={() => setOrdem("ticker")} ativo={ordem === "ticker"}>Ativo</Th>
                <th className="px-4 py-3 text-right font-normal">Cotação</th>
                <th className="px-4 py-3 text-right font-normal">Teto Bazin <InfoTip termo="bazin" /></th>
                <th className="px-4 py-3 text-right font-normal">Teto projetivo <InfoTip termo="preco_teto_projetivo" /></th>
                <th className="px-4 py-3 text-right font-normal">Graham <InfoTip termo="graham" /></th>
                <Th onClick={() => setOrdem("margem_projetiva")} ativo={ordem === "margem_projetiva"} direita dica="margem_seguranca">
                  Margem de segurança
                </Th>
                <Th onClick={() => setOrdem("dy_projetado")} ativo={ordem === "dy_projetado"} direita dica="dividend_yield">
                  Dividendos projetados
                </Th>
                <Th onClick={() => setOrdem("score")} ativo={ordem === "score"} direita dica="score_alpha">
                  Score Alpha
                </Th>
              </tr>
            </thead>
            <tbody className={calculando ? "opacity-60" : ""}>
              {linhas.map((a) => (
                <tr key={a.ticker} className="border-b border-line/60 last:border-0 hover:bg-raised/50">
                  <td className="px-3 py-3">
                    <StarButton ticker={a.ticker} />
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/ativo/${a.ticker}`} className="font-semibold hover:text-brand">
                      {a.ticker}
                    </Link>
                    <div className="text-xs text-muted">{a.setor}</div>
                  </td>
                  <td className="px-4 py-3 text-right">{fmtPreco(a.cotacao, a.moeda)}</td>
                  <td className="px-4 py-3 text-right text-muted">{fmtPreco(a.preco_teto_bazin, a.moeda)}</td>
                  <td className="px-4 py-3 text-right font-medium">{fmtPreco(a.preco_teto_projetivo, a.moeda)}</td>
                  <td className="px-4 py-3 text-right text-muted">{fmtPreco(a.preco_justo_graham, a.moeda)}</td>
                  <td className="px-4 py-3 text-right">
                    <Margem valor={a.margem_projetiva} />
                    <div className="mt-1">
                      <MargemBadge margem={a.margem_projetiva} />
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {fmtPreco(a.dpa_projetado, a.moeda)}
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
  dica,
}: {
  children: React.ReactNode;
  onClick: () => void;
  ativo: boolean;
  direita?: boolean;
  dica?: ChaveTermo;
}) {
  return (
    <th className={`px-4 py-3 font-normal ${direita ? "text-right" : ""}`} aria-sort={ativo ? "descending" : "none"}>
      <button onClick={onClick} className={`inline-flex items-center gap-1 hover:text-text ${ativo ? "text-brand" : ""}`}>
        {children} <ArrowDownUp size={11} />
      </button>
      {dica && <InfoTip termo={dica} className="ml-1" />}
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
