"use client";

import { fmtNum, type EventoAgenda, type MacroAgenda, type PanoramaGlobal } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { JurosBolsaChart } from "@/components/charts";
import { Delta, Disclaimer, ErrorState, Icon3D, InfoTip, Loading, PageHeader, Panel, Pill, SourceBadge } from "@/components/ui";
import type { ChaveTermo } from "@/lib/glossario";

const ICONES: Record<string, string> = { bolsas: "bar-chart", moedas: "banknote", cripto: "coin", commodities: "gem", juros_eua: "bank", volatilidade: "fire" };
const DICAS: Record<string, ChaveTermo> = { juros_eua: "treasury", volatilidade: "vix" };

export default function MercadoPage() {
  const { data, error, loading, reload } = useApi<PanoramaGlobal>("/api/mercado");
  const { data: macro } = useApi<MacroAgenda>("/api/macro");

  return (
    <>
      <PageHeader
        icon="bar-chart"
        title="Mercado global"
        description="Bolsas, moedas, commodities e juros do mundo em um só lugar, para entender o cenário antes de olhar qualquer ação."
        aside={data && <SourceBadge fonte={data.fonte} />}
      />
      {loading && !data && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && <Conteudo d={data} macro={macro} />}
      <Disclaimer />
    </>
  );
}

function fmtValor(v: number, unidade: string) {
  const casas = unidade === "pts" ? (v >= 1000 ? 0 : 2) : unidade === "%" ? 2 : v >= 1000 ? 0 : 2;
  const n = fmtNum(v, casas);
  return unidade === "R$" ? `R$ ${n}` : unidade === "US$" ? `US$ ${n}` : unidade === "%" ? `${n}%` : n;
}

function Conteudo({ d, macro }: { d: PanoramaGlobal; macro?: MacroAgenda | null }) {
  const tom = d.risco.rotulo === "Apetite alto" ? "up" : d.risco.rotulo === "Apetite baixo" ? "down" : "muted";
  // posição do marcador no termômetro: pontos de -4 a +4
  const posicao = Math.max(0, Math.min(100, ((d.risco.pontos + 4) / 8) * 100));
  const serie = d.serie_juros_bolsa;
  const variacaoIbov = serie.length > 1 ? serie[serie.length - 1].ibovespa - 100 : 0;
  const variacaoJuro = serie.length > 1 ? serie[serie.length - 1].juro_10a_eua - serie[0].juro_10a_eua : 0;

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <Panel className="xl:col-span-3" title="Apetite a risco hoje" action={<InfoTip termo="risk_on_off" />}>
        <div className="grid gap-6 md:grid-cols-[1fr_1.2fr] md:items-center">
          <div>
            <div className="mb-2 flex items-center gap-3">
              <span className="wide text-3xl font-semibold">{d.risco.rotulo}</span>
              <Pill tone={tom}>{d.risco.pontos > 0 ? "+" : ""}{d.risco.pontos} pontos</Pill>
            </div>
            <div className="relative mt-4 h-2.5 rounded-full bg-gradient-to-r from-down via-raised to-up" role="img" aria-label={`Termômetro: ${d.risco.rotulo}`}>
              <span className="absolute top-1/2 h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-surface bg-text shadow" style={{ left: `${posicao}%` }} />
            </div>
            <div className="mt-1.5 flex justify-between text-[11px] text-muted"><span>fuga de risco</span><span>neutro</span><span>busca por risco</span></div>
          </div>
          <ul className="space-y-1.5 text-sm text-muted">
            {d.risco.motivos.map((m) => (
              <li key={m} className="flex gap-2"><span className="text-brand">›</span> {m}</li>
            ))}
          </ul>
        </div>
      </Panel>

      {d.grupos.map((g) => (
        <Panel key={g.id} className={g.id === "bolsas" ? "xl:col-span-2 xl:row-span-2" : ""}>
          <div className="mb-3 flex items-start justify-between">
            <h2 className="flex items-center gap-1.5 text-[15px] font-semibold">
              {g.titulo} {DICAS[g.id] && <InfoTip termo={DICAS[g.id]} />}
            </h2>
            <Icon3D name={ICONES[g.id] ?? "bar-chart"} size={g.id === "bolsas" ? 72 : 56} className="-mr-1 -mt-2" />
          </div>
          <ul className={`divide-y divide-line ${g.id === "bolsas" ? "md:columns-2 md:gap-8 md:[&>li]:break-inside-avoid md:divide-y-0 [&>li]:border-b [&>li]:border-line" : ""}`}>
            {g.itens.map((i) => (
              <li key={i.simbolo} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                <span className="min-w-0 truncate">{i.nome}</span>
                <span className="flex shrink-0 items-baseline gap-3">
                  <span className="font-semibold">{fmtValor(i.valor, i.unidade)}</span>
                  <span className="w-16 text-right text-xs">
                    {i.tipo_variacao === "pp" ? (
                      <span className={i.variacao > 0 ? "text-down" : i.variacao < 0 ? "text-up" : "text-muted"} title="Juro subindo costuma pressionar a bolsa">
                        {i.variacao > 0 ? "+" : ""}{fmtNum(i.variacao, 2)} p.p.
                      </span>
                    ) : (
                      <Delta value={i.variacao} />
                    )}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      ))}

      <Panel className="xl:col-span-3" title="Juros dos EUA × Ibovespa (6 meses)">
        <div className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
          {serie.length > 1 ? <JurosBolsaChart dados={serie} /> : <p className="py-10 text-sm text-muted">Série indisponível no momento.</p>}
          <div className="text-sm leading-relaxed text-muted">
            <p>
              Quando os juros sobem, a renda fixa passa a pagar mais e o dinheiro estrangeiro tem uma alternativa segura: a bolsa de países emergentes costuma sofrer.
              Quando caem, acontece o contrário. A relação <strong className="text-text">não é perfeita</strong>, mas é uma das mais observadas pelo mercado.
            </p>
            {serie.length > 1 && (
              <p className="mt-3 rounded-xl bg-raised p-3">
                No período: Ibovespa <strong className={variacaoIbov >= 0 ? "text-up" : "text-down"}>{variacaoIbov >= 0 ? "+" : ""}{fmtNum(variacaoIbov, 1)}%</strong>,
                juro de 10 anos dos EUA <strong className="text-text">{variacaoJuro >= 0 ? "subiu" : "caiu"} {fmtNum(Math.abs(variacaoJuro), 2)} p.p.</strong>
              </p>
            )}
          </div>
        </div>
      </Panel>

      <FocusCard macro={macro} />
      <AgendaCard macro={macro} />
    </div>
  );
}

function FocusCard({ macro }: { macro?: MacroAgenda | null }) {
  const f = macro?.focus;
  return (
    <Panel className="xl:col-span-3" title="O que o mercado espera: Boletim Focus" action={<InfoTip termo="focus" />}>
      {!f ? (
        <p className="text-sm text-muted">Carregando expectativas…</p>
      ) : (
        <>
          <p className="mb-4 max-w-3xl text-sm leading-relaxed text-muted">
            Projeções de economistas para os próximos anos (mediana, com a faixa de mínima a máxima). É a melhor referência gratuita do que o mercado espera
            para os juros. Boletim de {new Date(f.data_boletim + "T12:00:00").toLocaleDateString("pt-BR")}.
          </p>
          <div className="scroll-thin overflow-x-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="text-left text-xs text-muted">
                <tr className="border-b border-line">
                  <th className="py-2 font-normal">Indicador</th>
                  {f.indicadores[0]?.anos.map((a) => <th key={a.ano} className="py-2 text-right font-normal">{a.ano}</th>)}
                </tr>
              </thead>
              <tbody>
                {f.indicadores.map((ind) => (
                  <tr key={ind.indicador} className="border-b border-line/60 last:border-0">
                    <td className="py-3">
                      <span className="font-medium">{ind.indicador}</span>
                      <span className="block text-xs text-muted">{ind.unidade}</span>
                    </td>
                    {ind.anos.map((a) => (
                      <td key={a.ano} className="py-3 text-right">
                        <span className="font-semibold">{fmtNum(a.mediana, 2)}</span>
                        <span className="block text-[11px] text-muted">{fmtNum(a.minimo, 2)} a {fmtNum(a.maximo, 2)}</span>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Panel>
  );
}

function AgendaCard({ macro }: { macro?: MacroAgenda | null }) {
  const eventos = macro?.agenda.eventos ?? [];
  const porDia = eventos.reduce<Record<string, EventoAgenda[]>>((acc, e) => {
    const dia = e.quando.slice(0, 10);
    (acc[dia] ??= []).push(e);
    return acc;
  }, {});
  return (
    <Panel className="xl:col-span-3" title="Agenda econômica da semana">
      <p className="mb-4 max-w-3xl text-sm leading-relaxed text-muted">
        Eventos de impacto médio e alto no exterior (inflação, emprego, PIB, decisões de juros). Horários de Brasília. A agenda brasileira não tem fonte
        gratuita estruturada: para o Brasil, use as expectativas do Focus acima.
      </p>
      {eventos.length === 0 ? (
        <p className="py-6 text-sm text-muted">{macro ? "Nenhum evento relevante listado agora, ou a fonte está indisponível." : "Carregando agenda…"}</p>
      ) : (
        <div className="grid gap-x-10 gap-y-5 lg:grid-cols-2">
          {Object.entries(porDia).map(([dia, lista]) => (
            <section key={dia}>
              <h3 className="mb-1 border-b border-line pb-1.5 text-sm font-semibold capitalize">
                {new Date(dia + "T12:00:00").toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" })}
              </h3>
              <ul className="divide-y divide-line/60">
                {lista.map((e, i) => (
                  <li key={i} className="flex items-start gap-3 py-2.5 text-sm">
                    <span className="w-11 shrink-0 pt-0.5 text-xs text-muted">{e.quando.slice(11)}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block font-medium leading-snug">{e.evento}</span>
                      <span className="text-xs text-muted">
                        {e.pais}
                        {e.previsto && ` · previsto ${e.previsto}`}
                        {e.anterior && ` · anterior ${e.anterior}`}
                      </span>
                    </span>
                    <Pill tone={e.impacto === "alto" ? "down" : "warn"}>{e.impacto === "alto" ? "impacto alto" : "impacto médio"}</Pill>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </Panel>
  );
}
