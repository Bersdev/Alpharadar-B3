"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Cpu, Loader2 } from "lucide-react";
import { api, fmtBRL, fmtNum, fmtPct, fmtPreco, type DetalheAtivo, type RespostaIA, type Valuation } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { TICKERS } from "@/lib/tickers";
import { DividendChart, PriceChart, ScoreRadar } from "@/components/charts";
import { AnalysisView } from "@/components/AnalysisView";
import type { ChaveTermo } from "@/lib/glossario";
import { Delta, Disclaimer, ErrorState, InfoTip, Loading, Panel, SourceBadge, StarButton } from "@/components/ui";

export function DossieAtivo() {
  const params = useParams<{ ticker: string }>();
  const ticker = (params.ticker ?? "BBAS3").toUpperCase();
  const router = useRouter();
  const { data, error, loading, reload } = useApi<DetalheAtivo>(`/api/assets/${encodeURIComponent(ticker)}`);

  return (
    <>
      <div className="mb-6 flex justify-end">
        <label className="flex items-center gap-2 text-sm text-muted">
          Trocar ativo
          <select
            value={ticker}
            onChange={(e) => router.push(`/ativo/${e.target.value}`)}
            className="rounded-md border border-line bg-surface px-2 py-1.5 text-text"
          >
            {TICKERS.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
      </div>
      {loading && !data && <Loading label={`Montando o dossiê de ${ticker}`} />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && data.ativo.ticker === ticker && <Conteudo d={data} />}
      <Disclaimer />
    </>
  );
}

function Conteudo({ d }: { d: DetalheAtivo }) {
  const { ativo, valuation: v, risco } = d;
  const eFii = ativo.tipo === "fii";
  const eua = ativo.mercado === "EUA";
  const fmtM = (x: number | null | undefined) => fmtPreco(x, ativo.moeda);

  return (
    <div className="flex flex-col gap-6">
      {/* Cabeçalho: o ticker é o título da página */}
      <header className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="text-sm text-muted">
            {ativo.nome}, {eFii ? "fundo imobiliário" : eua ? "ação negociada nos EUA" : "ação da B3"} do setor {ativo.setor}
          </p>
          <div className="flex items-center gap-2">
            <h1 className="wide text-5xl font-semibold tracking-tight">{ativo.ticker}</h1>
            <StarButton ticker={ativo.ticker} className="mt-2 !h-9 !w-9" />
          </div>
        </div>
        <div className="flex items-end gap-6">
          <div className="text-right">
            <div className="wide text-3xl font-semibold">{fmtM(ativo.cotacao)}</div>
            {eua && ativo.cotacao_brl != null && (
              <div className="text-xs text-muted">cerca de {fmtBRL(ativo.cotacao_brl)} no câmbio de hoje</div>
            )}
            <div className="text-sm">
              <Delta value={ativo.variacao_dia} /> <span className="text-muted">hoje</span>
            </div>
          </div>
          <SourceBadge fonte={d.historico.fonte} />
        </div>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Panel title="Cotação em 12 meses">
          <PriceChart dados={d.historico.precos} moeda={ativo.moeda} />
          <h3 className="mb-1 mt-5 text-sm text-muted">
            Proventos dos últimos 2 anos ({fmtM(d.historico.dpa_12m)} por {eFii ? "cota" : "ação"} nos últimos 12 meses)
          </h3>
          {d.historico.dividendos.length ? (
            <DividendChart dados={d.historico.dividendos} moeda={ativo.moeda} />
          ) : (
            <p className="py-6 text-sm text-muted">Nenhum provento registrado no período.</p>
          )}
        </Panel>

        <Panel title="Score Alpha">
          <div className="flex items-baseline gap-2">
            <span className="wide text-5xl font-semibold text-brand">{Math.round(v.score.total)}</span>
            <span className="text-muted">de 100, {v.score.classificacao.toLowerCase()}</span>
          </div>
          <ScoreRadar pilares={v.score.pilares} />
          <ul className="flex flex-col gap-2 text-sm">
            {v.score.pilares.map((p) => (
              <li key={p.nome} className="grid grid-cols-[1fr_auto] gap-x-3">
                <span>{p.nome}</span>
                <span className="font-semibold">{fmtNum(p.pontos, 1)}/20</span>
                <span className="col-span-2 text-xs text-muted">{p.explicacao}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1fr]">
        <SimuladorAtivo key={ativo.ticker} ticker={ativo.ticker} base={v} lpa={ativo.lpa} moeda={ativo.moeda} />
        <Panel title="Valuation e risco">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-4 text-sm">
            <Dado dica="bazin" rotulo="Preço-teto Bazin" valor={fmtM(v.preco_teto_bazin)} extra={`margem ${fmtPct(v.margem_bazin)}`} />
            <Dado dica="graham" rotulo="Preço justo de Graham" valor={fmtM(v.preco_justo_graham)} extra={eFii ? "não se aplica a FIIs" : `margem ${fmtPct(v.margem_graham)}`} />
            <Dado dica="pl" rotulo="P/L e P/VP" valor={`${fmtNum(ativo.pl, 1)} e ${fmtNum(ativo.pvp)}`} />
            <Dado dica="roe" rotulo="ROE" valor={fmtPct(ativo.roe)} />
            <Dado dica="volatilidade" rotulo="Volatilidade anual" valor={fmtPct(risco.volatilidade_anual)} />
            <Dado dica="drawdown" rotulo="Maior queda em 12 meses" valor={fmtPct(risco.max_drawdown)} />
            <Dado rotulo="Retorno em 12 meses" valor={fmtPct(risco.retorno_periodo)} />
            <Dado
              dica="divida_ebitda"
              rotulo="Dívida líquida / EBITDA"
              valor={ativo.divida_liquida_ebitda == null ? "não se aplica" : `${fmtNum(ativo.divida_liquida_ebitda, 1)}x`}
            />
          </dl>
          <p className="mt-4 text-xs text-muted">
            Fundamentos: {ativo.fonte_fundamentos === "ao_vivo" ? "atualizados do Yahoo Finance (último balanço publicado)" : "dados de reserva, podem estar defasados"}.
          </p>
          <div className="mt-4 rounded-lg bg-raised p-3 text-sm">
            <span className="font-semibold">Contra uma LCI a 92% do CDI{eua ? " (dividendos já sem os 30% de IR retido nos EUA)" : ""}: </span>
            <span className={d.premio_lci.premio_pp >= 0 ? "text-up" : "text-down"}>
              {d.premio_lci.premio_pp > 0 ? "+" : ""}
              {fmtNum(d.premio_lci.premio_pp)} p.p.
            </span>
            <p className="mt-1 text-muted">{d.premio_lci.leitura}</p>
          </div>
        </Panel>
      </div>

      <Panel title={`Notícias que afetam ${ativo.ticker}`}>
        {d.noticias.length === 0 ? (
          <p className="text-sm text-muted">Nenhuma notícia recente mapeada para este ativo.</p>
        ) : (
          <ul className="divide-y divide-line">
            {d.noticias.map((n) => (
              <li key={n.id} className="flex gap-3 py-3 first:pt-0 last:pb-0">
                <span className={`mt-0.5 text-xs font-semibold ${n.efeito_no_ativo === "beneficiado" ? "text-up" : "text-down"}`}>
                  {n.efeito_no_ativo === "beneficiado" ? "▲" : "▼"}
                </span>
                <div>
                  <p className="font-medium">{n.titulo}</p>
                  <p className="text-sm text-muted">{n.resumo}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <AnaliseIA key={ativo.ticker} ticker={ativo.ticker} />
    </div>
  );
}

function Dado({ rotulo, valor, extra, dica }: { rotulo: string; valor: string; extra?: string; dica?: ChaveTermo }) {
  return (
    <div>
      <dt className="text-muted">
        {rotulo} {dica && <InfoTip termo={dica} />}
      </dt>
      <dd className="mt-0.5 font-semibold">{valor}</dd>
      {extra && <dd className="text-xs text-muted">{extra}</dd>}
    </div>
  );
}

/** Ajuste de payout, crescimento e yield: recalcula o preço-teto projetivo deste ativo no Python. */
function SimuladorAtivo({ ticker, base, lpa, moeda }: { ticker: string; base: Valuation; lpa: number; moeda: string }) {
  const fmtM = (x: number | null | undefined) => fmtPreco(x, moeda);
  const [payout, setPayout] = useState(base.premissas.payout_pct);
  const [cresc, setCresc] = useState(Math.round(base.premissas.crescimento_g * 100));
  const [yieldPct, setYieldPct] = useState(base.premissas.yield_desejado * 100);
  const [res, setRes] = useState<Valuation>(base);

  useEffect(() => {
    const t = setTimeout(async () => {
      try {
        const r = await api<{ resultados: Valuation[] }>("/api/simulate/valuation", {
          ticker,
          payout_pct: payout,
          crescimento_g: cresc / 100,
          yield_desejado: yieldPct / 100,
        });
        setRes(r.resultados[0]);
      } catch {
        /* mantém o último resultado válido */
      }
    }, 250);
    return () => clearTimeout(t);
  }, [ticker, payout, cresc, yieldPct]);

  const controles = [
    { rotulo: "Payout", valor: payout, set: setPayout, min: 0, max: 100, step: 5, fmt: `${payout}% do lucro` },
    { rotulo: "Crescimento do lucro", valor: cresc, set: setCresc, min: -10, max: 20, step: 1, fmt: `${cresc > 0 ? "+" : ""}${cresc}%` },
    { rotulo: "Yield exigido", valor: yieldPct, set: setYieldPct, min: 5, max: 12, step: 0.5, fmt: fmtPct(yieldPct) },
  ];

  return (
    <Panel title="Simulador de preço-teto projetivo">
      <div className="flex flex-col gap-4">
        {controles.map((c) => (
          <label key={c.rotulo} className="block text-sm">
            <span className="mb-1 flex justify-between">
              {c.rotulo} <span className="font-semibold text-brand">{c.fmt}</span>
            </span>
            <input type="range" className="w-full" min={c.min} max={c.max} step={c.step} value={c.valor} onChange={(e) => c.set(Number(e.target.value))} />
          </label>
        ))}
      </div>
      <div className="mt-5 grid grid-cols-2 gap-4 border-t border-line pt-4">
        <div>
          <div className="text-sm text-muted">Preço-teto projetivo</div>
          <div className="wide text-2xl font-semibold">{fmtM(res.preco_teto_projetivo)}</div>
          <div className={`text-sm ${(res.margem_projetiva ?? 0) >= 0 ? "text-up" : "text-down"}`}>
            margem de {fmtPct(res.margem_projetiva)}
          </div>
        </div>
        <div>
          <div className="text-sm text-muted">Dividendo projetado</div>
          <div className="wide text-2xl font-semibold">{fmtM(res.dpa_projetado)}</div>
          <div className="text-sm text-muted">{fmtPct(res.dy_projetado)} ao ano, score {Math.round(res.score.total)}</div>
        </div>
      </div>
      <p className="mt-4 text-xs text-muted">
        Conta feita no backend: {fmtM(lpa)} (LPA) × (1 {cresc >= 0 ? "+" : "−"} {Math.abs(cresc)}%) × {payout}% ÷ {fmtPct(yieldPct)}.
      </p>
    </Panel>
  );
}

function AnaliseIA({ ticker }: { ticker: string }) {
  const [resp, setResp] = useState<RespostaIA | null>(null);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function gerar() {
    setCarregando(true);
    setErro(null);
    try {
      setResp(await api<RespostaIA>("/api/ai/analyze", { pergunta: `Avalie o histórico e o risco de ${ticker}`, ticker }));
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
    } finally {
      setCarregando(false);
    }
  }

  return (
    <Panel
      title="Análise de risco"
      action={
        <button
          onClick={gerar}
          disabled={carregando}
          className="inline-flex items-center gap-2 rounded-md bg-brand px-3.5 py-2 text-sm font-semibold text-white hover:brightness-110 disabled:opacity-60"
        >
          {carregando ? <Loader2 size={15} className="animate-spin" /> : <Cpu size={15} />}
          {carregando ? "Gerando análise…" : "Gerar análise de risco via IA Python"}
        </button>
      }
    >
      {erro && <ErrorState message={erro} />}
      {resp ? (
        <AnalysisView r={resp} />
      ) : (
        !erro && (
          <p className="text-sm text-muted">
            O copiloto cruza histórico, valuation, endividamento e notícias de {ticker} e escreve um relatório de pontos fortes e de atenção.
          </p>
        )
      )}
    </Panel>
  );
}
