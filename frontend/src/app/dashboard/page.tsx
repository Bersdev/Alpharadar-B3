"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { BarChart3, DollarSign, Percent } from "lucide-react";
import { fmtNum, fmtPct, fmtPreco, fmtSinal, type AtivoAvaliado, type Overview, type ResumoAtivo } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Delta, Disclaimer, ErrorState, Loading, PageHeader, Panel, Pill, SourceBadge, TickerChip } from "@/components/ui";

export default function DashboardPage() {
  const { data, error, loading, reload } = useApi<Overview>("/api/overview");
  const { data: ranking } = useApi<{ ativos: AtivoAvaliado[] }>("/api/assets");

  return (
    <>
      <PageHeader
        title="Pulso do mercado"
        description="Juros, câmbio, bolsa e as notícias que mexem com os seus ativos, em uma tela."
        aside={data && (
          <div className="flex flex-col items-end gap-1 text-xs text-muted">
            <SourceBadge fonte={data.fonte_cotacoes === "ao_vivo" && data.macro.fontes.bcb === "ao_vivo" ? "ao_vivo" : data.fonte_cotacoes} />
            Atualizado às {data.atualizado_em.slice(11, 16)}
          </div>
        )}
      />
      {loading && !data && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && <Conteudo d={data} ranking={ranking?.ativos ?? []} />}
      <Disclaimer />
    </>
  );
}

function Conteudo({ d, ranking }: { d: Overview; ranking: AtivoAvaliado[] }) {
  const m = d.macro;
  // Parcela da Selic "consumida" pela inflação: o que sobra é o juro real.
  const inflacaoNaSelic = Math.min(100, Math.max(0, (m.ipca_12m / m.selic_anual) * 100));

  return (
    <div className="flex flex-col gap-8">
      <section className="grid gap-4 md:grid-cols-3">
        <CartaoIndicador
          icone={<BarChart3 size={14} className="text-brand" />}
          titulo="Ibovespa"
          selo={<Delta value={m.ibovespa_var} />}
          valor={fmtNum(m.ibovespa, 0)}
          legenda={<>pontos, <Delta value={m.ibovespa_var} /> no dia</>}
        />
        <CartaoIndicador
          icone={<DollarSign size={14} className="text-up" />}
          titulo="Dólar"
          selo={<Delta value={m.dolar_var} />}
          valor={`R$ ${fmtNum(m.dolar)}`}
          legenda={<>IFIX de referência: {fmtNum(m.ifix, 0)} pontos</>}
        />
        <CartaoIndicador
          icone={<Percent size={14} className="text-warn" />}
          titulo="Selic"
          valor={fmtPct(m.selic_anual, 2)}
          legenda={<>CDI {fmtPct(m.cdi_anual, 2)}, IPCA {fmtPct(m.ipca_12m, 2)} em 12 meses</>}
        >
          <div className="mt-4 h-2 rounded-full bg-raised" role="img" aria-label={`Inflação equivale a ${fmtNum(inflacaoNaSelic, 0)}% da Selic`}>
            <div className="h-2 rounded-full bg-up" style={{ width: `${inflacaoNaSelic}%` }} />
          </div>
          <p className="mt-2 text-xs text-muted">Juro real de {fmtPct(m.juro_real, 2)} ao ano</p>
        </CartaoIndicador>
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="wide text-lg font-semibold">Quadro do dia</h2>
          <Link href="/preco-teto" className="text-sm text-muted hover:text-text">Ver todos os ativos</Link>
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Coluna titulo="Maiores altas" total={d.maiores_altas.length}>
            {d.maiores_altas.slice(0, 3).map((a) => <CartaoMovimento key={a.ticker} a={a} />)}
          </Coluna>
          <Coluna titulo="Maiores baixas" total={d.maiores_baixas.length}>
            {d.maiores_baixas.slice(0, 3).map((a) => <CartaoMovimento key={a.ticker} a={a} />)}
          </Coluna>
          <Coluna titulo="Melhores Score Alpha" total={ranking.length}>
            {ranking.slice(0, 3).map((a) => <CartaoScore key={a.ticker} a={a} />)}
            {ranking.length === 0 && <p className="p-2 text-sm text-muted">Calculando scores…</p>}
          </Coluna>
          <Coluna titulo="Manchetes de alto impacto" total={d.manchetes_urgentes.length}>
            {d.manchetes_urgentes.slice(0, 3).map((n) => (
              <Cartao
                key={n.id}
                topo={n.categoria}
                selo={<Pill tone={n.sentimento_rotulo === "Positivo" ? "up" : n.sentimento_rotulo === "Negativo" ? "down" : "muted"}>{n.sentimento_rotulo}</Pill>}
                titulo={n.titulo}
                rodape={<div className="flex flex-wrap gap-1">{n.ativos_afetados.slice(0, 3).map((a) => <TickerChip key={a.ticker} ticker={a.ticker} efeito={a.efeito} />)}</div>}
              />
            ))}
          </Coluna>
        </div>
      </section>

      <Cenario d={d} />
    </div>
  );
}

function CartaoIndicador({ icone, titulo, selo, valor, legenda, children }: {
  icone: ReactNode; titulo: string; selo?: ReactNode; valor: string; legenda: ReactNode; children?: ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-5">
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm text-muted">
          <span className="grid h-6 w-6 place-items-center rounded-md bg-raised">{icone}</span> {titulo}
        </span>
        {selo && <span className="rounded-md border border-line px-2 py-0.5 text-xs">{selo}</span>}
      </div>
      <div className="wide mt-5 text-[2.5rem] font-semibold leading-none">{valor}</div>
      <p className="mt-3 text-sm text-muted">{legenda}</p>
      {children}
    </div>
  );
}

function Coluna({ titulo, total, children }: { titulo: string; total: number; children: ReactNode }) {
  return (
    <div className="rounded-2xl border border-line bg-surface p-2.5">
      <div className="flex items-center justify-between px-2 pb-2.5 pt-1.5 text-sm">
        <span className="font-medium">
          {titulo} <span className="ml-1 rounded bg-raised px-1.5 py-0.5 text-[11px] text-muted">{total}</span>
        </span>
      </div>
      <div className="flex flex-col gap-2.5">{children}</div>
    </div>
  );
}

function Cartao({ topo, selo, titulo, valor, barra, rodape, href }: {
  topo: string; selo?: ReactNode; titulo: string; valor?: string; barra?: { pct: number; cor: string };
  rodape?: ReactNode; href?: string;
}) {
  const conteudo = (
    <>
      <div className="flex items-center justify-between gap-2 text-xs text-muted">
        <span className="truncate">{topo}</span>
        {selo}
      </div>
      <p className={`mt-3 ${valor ? "text-sm text-muted" : "text-sm font-medium leading-snug"}`}>{titulo}</p>
      {valor && <p className="wide mt-0.5 text-2xl font-semibold">{valor}</p>}
      {barra && (
        <div className="mt-3 h-1.5 rounded-full bg-raised">
          <div className={`h-1.5 rounded-full ${barra.cor}`} style={{ width: `${barra.pct}%` }} />
        </div>
      )}
      {rodape && <div className="mt-3 border-t border-line/70 pt-2.5 text-xs text-muted">{rodape}</div>}
    </>
  );
  const classe = "block rounded-xl border border-line bg-bg p-3.5";
  return href ? <Link href={href} className={`${classe} hover:border-muted/40`}>{conteudo}</Link> : <div className={classe}>{conteudo}</div>;
}

function CartaoMovimento({ a }: { a: ResumoAtivo }) {
  return (
    <Cartao
      href={`/ativo/${a.ticker}`}
      topo={a.tipo === "fii" ? "Fundo imobiliário" : a.mercado === "EUA" ? "Ação dos EUA" : "Ação B3"}
      selo={<Pill tone={a.variacao_dia >= 0 ? "up" : "down"}>{fmtSinal(a.variacao_dia)}</Pill>}
      titulo={`${a.ticker}, ${a.nome}`}
      valor={fmtPreco(a.cotacao, a.moeda)}
      rodape={<span>Variação de hoje</span>}
    />
  );
}

function CartaoScore({ a }: { a: AtivoAvaliado }) {
  const tom = a.score.total >= 65 ? "up" : a.score.total >= 50 ? "warn" : "down";
  return (
    <Cartao
      href={`/ativo/${a.ticker}`}
      topo={a.setor}
      selo={<Pill tone={tom}>{a.score.classificacao}</Pill>}
      titulo={`${a.ticker}, score ${Math.round(a.score.total)} de 100`}
      valor={fmtPreco(a.preco_teto_projetivo, a.moeda)}
      barra={{ pct: a.score.total, cor: tom === "up" ? "bg-up" : tom === "warn" ? "bg-warn" : "bg-down" }}
      rodape={<span>Teto projetivo, margem de {fmtPct(a.margem_projetiva)}</span>}
    />
  );
}

/** Compara, em barras, quanto rende a renda fixa isenta frente aos dividendos da bolsa. */
function Cenario({ d }: { d: Overview }) {
  const c = d.cenario;
  const barras = [
    { nome: "LCI a 92% do CDI", valor: c.lci_92_cdi, cor: "bg-brand", detalhe: "isenta de IR, sem oscilação" },
    { nome: "Dividendos médios dos FIIs", valor: c.dy_medio_fiis, cor: "bg-up", detalhe: "projetados, isentos para pessoa física" },
    { nome: "Dividendos médios das ações", valor: c.dy_medio_acoes, cor: "bg-muted", detalhe: "projetados" },
  ];
  const maximo = Math.max(...barras.map((b) => b.valor), 1);
  return (
    <Panel title="Bolsa ou renda fixa isenta?">
      <p className="mb-5 max-w-2xl text-sm leading-relaxed text-muted">{c.leitura}</p>
      <div className="grid gap-x-10 gap-y-4 lg:grid-cols-[1.6fr_1fr]">
        <div className="flex flex-col gap-4">
          {barras.map((b) => (
            <div key={b.nome}>
              <div className="mb-1.5 flex items-baseline justify-between text-sm">
                <span>
                  {b.nome}
                  <span className="block text-xs text-muted">{b.detalhe}</span>
                </span>
                <span className="font-semibold">{fmtPct(b.valor, 2)} a.a.</span>
              </div>
              <div className="h-2 rounded-full bg-raised">
                <div className={`h-2 rounded-full ${b.cor}`} style={{ width: `${(b.valor / maximo) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
        <dl className="grid grid-cols-2 gap-4 self-start rounded-xl border border-line bg-bg p-4 text-sm lg:grid-cols-1">
          <div>
            <dt className="text-muted">Juro real (Selic menos IPCA)</dt>
            <dd className="wide mt-0.5 text-xl font-semibold">{fmtPct(d.macro.juro_real, 2)}</dd>
          </div>
          <div>
            <dt className="text-muted">CDB equivalente à LCI 92%</dt>
            <dd className="wide mt-0.5 text-xl font-semibold">{fmtPct(c.cdb_equivalente_lci_92)} do CDI</dd>
          </div>
        </dl>
      </div>
    </Panel>
  );
}
