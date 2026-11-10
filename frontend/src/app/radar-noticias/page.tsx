"use client";

import { useEffect, useMemo, useState } from "react";
import { Landmark } from "lucide-react";
import { type Noticia } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Disclaimer, ErrorState, Loading, PageHeader, Panel, TickerChip } from "@/components/ui";

interface Radar {
  noticias: Noticia[];
  resumo: {
    total: number;
    por_sentimento: Record<"Positivo" | "Neutro" | "Negativo", number>;
    mais_beneficiados: { ticker: string; indice: number }[];
    mais_prejudicados: { ticker: string; indice: number }[];
  };
}

type FiltroSent = "Todos" | Noticia["sentimento_rotulo"];
const COR_SENT = { Positivo: "text-up", Neutro: "text-muted", Negativo: "text-down" } as const;
const BARRA_SENT = { Positivo: "bg-up", Neutro: "bg-muted", Negativo: "bg-down" } as const;

export default function RadarNoticiasPage() {
  const { data, error, loading, reload } = useApi<Radar>("/api/news-radar");
  // Atualiza o radar sozinho a cada 60 s (o backend guarda o feed em cache por 2 min).
  useEffect(() => {
    const t = setInterval(reload, 60_000);
    return () => clearInterval(t);
  }, [reload]);
  const [filtro, setFiltro] = useState<FiltroSent>("Todos");
  const [soAlto, setSoAlto] = useState(false);

  const lista = useMemo(
    () =>
      (data?.noticias ?? []).filter(
        (n) => (filtro === "Todos" || n.sentimento_rotulo === filtro) && (!soAlto || n.impacto === "alto"),
      ),
    [data, filtro, soAlto],
  );
  const demonstracao = data?.noticias.some((n) => n.fonte === "demonstracao");
  const aoVivo = data?.noticias.some((n) => n.fonte === "rss" || n.fonte === "api");

  return (
    <>
      <PageHeader
        title="Radar de notícias"
        description="Cada evento econômico traduzido em consequência: quais ações, FIIs e produtos de renda fixa ganham ou perdem com ele."
      />
      {loading && !data && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <div className="order-2 flex min-w-0 flex-col gap-4 lg:order-1">
            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex rounded-lg border border-line p-0.5 text-sm" role="tablist" aria-label="Filtrar por sentimento">
                {(["Todos", "Positivo", "Neutro", "Negativo"] as FiltroSent[]).map((f) => (
                  <button
                    key={f}
                    role="tab"
                    aria-selected={filtro === f}
                    onClick={() => setFiltro(f)}
                    className={`rounded-md px-3 py-1.5 ${filtro === f ? "bg-raised text-text" : "text-muted hover:text-text"}`}
                  >
                    {f}
                  </button>
                ))}
              </div>
              <label className="flex items-center gap-2 text-sm text-muted">
                <input type="checkbox" checked={soAlto} onChange={(e) => setSoAlto(e.target.checked)} className="accent-[var(--brand)]" />
                Só impacto alto
              </label>
            </div>
            {aoVivo && (
              <p className="text-xs text-up">Manchetes reais (RSS e APIs de notícias), atualizadas automaticamente a cada minuto.</p>
            )}
            {demonstracao && (
              <p className="text-xs text-muted">
                Exibindo cenários de demonstração escritos pelo projeto. Configure NEWS_RSS_URLS no backend para ler manchetes reais.
              </p>
            )}
            {lista.length === 0 && <p className="py-10 text-muted">Nenhuma notícia com esses filtros. Troque o sentimento ou desmarque “Só impacto alto”.</p>}
            {lista.map((n) => (
              <CartaoNoticia key={n.id} n={n} />
            ))}
          </div>

          <aside className="order-1 flex flex-col gap-6 lg:order-2">
            <Panel title="Termômetro da semana">
              <div className="flex h-3 overflow-hidden rounded-full">
                {(["Positivo", "Neutro", "Negativo"] as const).map((s) => (
                  <div
                    key={s}
                    className={BARRA_SENT[s]}
                    style={{ width: `${(data.resumo.por_sentimento[s] / Math.max(data.resumo.total, 1)) * 100}%` }}
                  />
                ))}
              </div>
              <dl className="mt-3 grid grid-cols-3 text-center text-sm">
                {(["Positivo", "Neutro", "Negativo"] as const).map((s) => (
                  <div key={s}>
                    <dd className={`wide text-xl font-semibold ${COR_SENT[s]}`}>{data.resumo.por_sentimento[s]}</dd>
                    <dt className="text-xs text-muted">{s.toLowerCase()}</dt>
                  </div>
                ))}
              </dl>
            </Panel>
            <Panel title="Mais favorecidos">
              <Ranking itens={data.resumo.mais_beneficiados} efeito="beneficiado" />
            </Panel>
            <Panel title="Mais pressionados">
              <Ranking itens={data.resumo.mais_prejudicados} efeito="prejudicado" />
            </Panel>
          </aside>
        </div>
      )}
      <Disclaimer />
    </>
  );
}

function CartaoNoticia({ n }: { n: Noticia }) {
  const ganham = n.ativos_afetados.filter((a) => a.efeito === "beneficiado");
  const perdem = n.ativos_afetados.filter((a) => a.efeito === "prejudicado");
  const nivel = { baixo: 1, medio: 2, alto: 3 }[n.impacto];
  return (
    <article className="relative overflow-hidden rounded-2xl border border-line bg-surface p-5 pl-6">
      <span className={`absolute inset-y-0 left-0 w-1 ${BARRA_SENT[n.sentimento_rotulo]}`} aria-hidden="true" />
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span className={`font-semibold ${COR_SENT[n.sentimento_rotulo]}`}>{n.sentimento_rotulo}</span>
        <span>{n.categoria}{n.origem && n.origem !== "RSS" ? `, via ${n.origem}` : ""}</span>
        <span className="flex items-center gap-1" title={`Impacto ${n.impacto}`}>
          Impacto
          {[1, 2, 3].map((i) => (
            <span key={i} className={`h-2.5 w-1.5 rounded-sm ${i <= nivel ? "bg-brand" : "bg-raised"}`} />
          ))}
        </span>
        <time dateTime={n.data}>{new Date(n.data).toLocaleDateString("pt-BR", { day: "2-digit", month: "long" })}</time>
      </div>
      <h2 className="mt-2 text-lg font-semibold leading-snug">
        {n.link ? (
          <a href={n.link} target="_blank" rel="noopener noreferrer" className="hover:text-brand">
            {n.titulo}
          </a>
        ) : (
          n.titulo
        )}
      </h2>
      <p className="mt-1 max-w-3xl text-sm leading-relaxed text-muted">{n.resumo}</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <h3 className="mb-1.5 text-xs text-up">Ganham</h3>
          <div className="flex flex-wrap gap-1.5">
            {ganham.length ? ganham.map((a) => <TickerChip key={a.ticker} ticker={a.ticker} efeito="beneficiado" />) : <span className="text-xs text-muted">nenhum ativo monitorado</span>}
          </div>
        </div>
        <div>
          <h3 className="mb-1.5 text-xs text-down">Perdem</h3>
          <div className="flex flex-wrap gap-1.5">
            {perdem.length ? perdem.map((a) => <TickerChip key={a.ticker} ticker={a.ticker} efeito="prejudicado" />) : <span className="text-xs text-muted">nenhum ativo monitorado</span>}
          </div>
        </div>
      </div>
      <p className="mt-4 flex gap-2 rounded-lg bg-raised px-3 py-2 text-sm">
        <Landmark size={15} className="mt-0.5 shrink-0 text-brand" />
        <span>
          <span className="font-semibold">Renda fixa: </span>
          <span className="text-muted">{n.renda_fixa}</span>
        </span>
      </p>
    </article>
  );
}

function Ranking({ itens, efeito }: { itens: { ticker: string; indice: number }[]; efeito: "beneficiado" | "prejudicado" }) {
  if (!itens.length) return <p className="text-sm text-muted">Nenhum ativo nesta lista.</p>;
  return (
    <ul className="flex flex-col gap-2">
      {itens.map((i) => (
        <li key={i.ticker} className="flex items-center gap-3">
          <TickerChip ticker={i.ticker} efeito={efeito} />
          <div className="h-1.5 flex-1 rounded-full bg-raised">
            <div
              className={`h-1.5 rounded-full ${efeito === "beneficiado" ? "bg-up" : "bg-down"}`}
              style={{ width: `${Math.abs(i.indice) * 100}%` }}
            />
          </div>
        </li>
      ))}
    </ul>
  );
}
