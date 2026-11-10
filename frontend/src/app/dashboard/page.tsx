"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowUpRight, Check } from "lucide-react";
import { fmtNum, fmtPct, fmtPreco, fmtSinal, type AtivoAvaliado, type Overview, type ResumoAtivo } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Delta, Disclaimer, ErrorState, Icon3D, Loading, Pill, SourceBadge, TickerChip } from "@/components/ui";

export default function DashboardPage() {
  const { data, error, loading, reload } = useApi<Overview>("/api/overview");
  const { data: ranking } = useApi<{ ativos: AtivoAvaliado[] }>("/api/assets");

  return (
    <>
      {data && (
        <div className="mb-4 flex flex-wrap items-center justify-end gap-3 text-xs text-muted">
          Atualizado às {data.atualizado_em.slice(11, 16)}
          <SourceBadge fonte={data.fonte_cotacoes === "ao_vivo" && data.macro.fontes.bcb === "ao_vivo" ? "ao_vivo" : data.fonte_cotacoes} />
        </div>
      )}
      {loading && !data && <Loading />}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && <Conteudo d={data} ranking={ranking?.ativos ?? []} />}
      <Disclaimer />
    </>
  );
}

/** Número grande no estilo da referência: prefixo e decimais em cinza, parte inteira em destaque. */
function GrandeNumero({ valor, casas = 2, prefixo, sufixo }: { valor: number; casas?: number; prefixo?: string; sufixo?: string }) {
  const [inteiro, decimais] = fmtNum(valor, casas).split(",");
  return (
    <div className="wide flex items-baseline leading-none">
      {prefixo && <span className="mr-2 text-[1.6rem] font-semibold text-muted">{prefixo}</span>}
      <span className="text-[3.4rem] font-semibold">{inteiro}</span>
      {decimais && <span className="text-[1.6rem] font-semibold text-muted">,{decimais}</span>}
      {sufixo && <span className="ml-1 text-base font-medium text-muted">{sufixo}</span>}
    </div>
  );
}

function Conteudo({ d, ranking }: { d: Overview; ranking: AtivoAvaliado[] }) {
  const m = d.macro;
  const c = d.cenario;
  const opcoes = [
    { nome: "LCI a 92% do CDI", valor: c.lci_92_cdi, cor: "bg-brand", ponto: "bg-brand", nota: "isenta de IR, sem oscilação" },
    { nome: "Dividendos dos FIIs", valor: c.dy_medio_fiis, cor: "bg-up", ponto: "bg-up", nota: "projetados, isentos para PF" },
    { nome: "Dividendos das ações", valor: c.dy_medio_acoes, cor: "bg-warn", ponto: "bg-warn", nota: "projetados, B3" },
  ];
  const total = opcoes.reduce((s, o) => s + o.valor, 0) || 1;

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      {/* Cartão principal: Ibovespa e comparação entre bolsa e renda fixa isenta */}
      <Cartao className="xl:col-span-2" titulo="Ibovespa" icone="chart-up" iconeTamanho={108}>
        <div className="flex flex-wrap items-end gap-x-6 gap-y-2">
          <GrandeNumero valor={m.ibovespa} casas={0} sufixo="pontos" />
          <div className="mb-1 border-l border-line pl-4 text-sm">
            <span className="flex items-center gap-1 font-medium">
              <ArrowUpRight size={15} className={m.ibovespa_var >= 0 ? "text-up" : "rotate-90 text-down"} />
              <Delta value={m.ibovespa_var} /> no dia
            </span>
            <span className="text-muted">IFIX de referência: {fmtNum(m.ifix, 0)} pontos</span>
          </div>
        </div>

        <div className="mt-7">
          <div className="mb-2 flex items-baseline justify-between text-sm">
            <span className="font-medium">Quanto cada opção rende por ano</span>
            <span className="text-muted">juro real de {fmtPct(m.juro_real, 2)}</span>
          </div>
          <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full" role="img" aria-label="Comparação de rendimentos anuais">
            {opcoes.map((o) => (
              <div key={o.nome} className={o.cor} style={{ width: `${(o.valor / total) * 100}%` }} />
            ))}
          </div>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            {opcoes.map((o) => (
              <div key={o.nome}>
                <p className="flex items-center gap-1.5 text-xs text-muted">
                  <span className={`h-2 w-2 rounded-full ${o.ponto}`} /> {o.nome}
                </p>
                <p className="wide mt-0.5 text-lg font-semibold">{fmtPct(o.valor, 2)} <span className="text-xs font-normal text-muted">a.a.</span></p>
                <p className="text-xs text-muted">{o.nota}</p>
              </div>
            ))}
          </div>
          <p className="mt-4 max-w-2xl text-[13px] leading-relaxed text-muted">{c.leitura}</p>
        </div>
      </Cartao>

      {/* Câmbio e juros, como a lista "Contas a pagar" da referência */}
      <Cartao titulo="Câmbio e juros" icone="banknote">
        <GrandeNumero valor={m.dolar} prefixo="R$" />
        <p className="mt-2 text-sm text-muted">
          dólar hoje, <Delta value={m.dolar_var} />
        </p>
        <ul className="mt-5 divide-y divide-line text-sm">
          {[
            ["Selic", fmtPct(m.selic_anual, 2), "meta do Copom"],
            ["CDI", fmtPct(m.cdi_anual, 2), "ao ano"],
            ["IPCA em 12 meses", fmtPct(m.ipca_12m, 2), "inflação"],
            ["Juro real", fmtPct(m.juro_real, 2), "Selic menos IPCA"],
          ].map(([nome, valor, nota]) => (
            <li key={nome} className="flex items-center gap-3 py-2.5">
              <span className="grid h-5 w-5 place-items-center rounded-full border border-line text-up">
                {nome === "Juro real" && <Check size={12} strokeWidth={3} />}
              </span>
              <span className="flex-1">
                {nome} <span className="text-xs text-muted">{nota}</span>
              </span>
              <span className="font-semibold">{valor}</span>
            </li>
          ))}
        </ul>
      </Cartao>

      <Cartao titulo="Maiores altas" icone="chart-up" iconeTamanho={64}>
        <ListaMovimentos itens={d.maiores_altas} />
      </Cartao>

      <Cartao titulo="Maiores baixas" icone="chart-down" iconeTamanho={64}>
        <ListaMovimentos itens={d.maiores_baixas} />
      </Cartao>

      <Cartao titulo="Melhores Score Alpha" icone="trophy" iconeTamanho={64}>
        {ranking.length === 0 ? (
          <p className="text-sm text-muted">Calculando scores…</p>
        ) : (
          <ul className="flex flex-col gap-3.5">
            {ranking.slice(0, 5).map((a) => {
              const tom = a.score.total >= 65 ? "bg-up" : a.score.total >= 50 ? "bg-warn" : "bg-down";
              return (
                <li key={a.ticker}>
                  <Link href={`/ativo/${a.ticker}`} className="group block">
                    <div className="flex items-baseline justify-between text-sm">
                      <span className="font-semibold group-hover:text-brand">{a.ticker}</span>
                      <span className="font-semibold">
                        {Math.round(a.score.total)}
                        <span className="text-xs font-normal text-muted"> /100</span>
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 rounded-full bg-raised">
                      <div className={`h-1.5 rounded-full ${tom}`} style={{ width: `${a.score.total}%` }} />
                    </div>
                    <p className="mt-1 text-xs text-muted">
                      {a.score.classificacao}, teto projetivo {fmtPreco(a.preco_teto_projetivo, a.moeda)}
                    </p>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </Cartao>

      <Cartao className="xl:col-span-3" titulo="Manchetes de alto impacto" icone="news" iconeTamanho={64}
        acao={<Link href="/radar-noticias" className="text-sm font-medium text-brand hover:underline">Abrir radar completo</Link>}>
        <ul className="grid gap-x-8 md:grid-cols-2">
          {d.manchetes_urgentes.map((n) => (
            <li key={n.id} className="flex flex-col gap-2 border-t border-line py-3.5 first:border-t-0 md:[&:nth-child(2)]:border-t-0">
              <div className="flex items-center gap-2 text-xs text-muted">
                <Pill tone={n.sentimento_rotulo === "Positivo" ? "up" : n.sentimento_rotulo === "Negativo" ? "down" : "muted"}>
                  {n.sentimento_rotulo}
                </Pill>
                {n.categoria}
              </div>
              <p className="text-[15px] font-medium leading-snug">{n.titulo}</p>
              {n.ativos_afetados.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {n.ativos_afetados.slice(0, 5).map((a) => (
                    <TickerChip key={a.ticker} ticker={a.ticker} efeito={a.efeito} />
                  ))}
                </div>
              )}
            </li>
          ))}
        </ul>
      </Cartao>
    </div>
  );
}

/** Cartão da grade: título, ação opcional e ícone 3D no canto, como nos cartões da referência. */
function Cartao({ titulo, icone, iconeTamanho = 80, acao, className = "", children }: {
  titulo: string; icone: string; iconeTamanho?: number; acao?: ReactNode; className?: string; children: ReactNode;
}) {
  return (
    <section className={`card p-5 ${className}`}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h2 className="text-[15px] font-semibold">{titulo}</h2>
          {acao && <div className="mt-1">{acao}</div>}
        </div>
        <Icon3D name={icone} size={iconeTamanho} className="-mr-1 -mt-2" />
      </div>
      {children}
    </section>
  );
}

function ListaMovimentos({ itens }: { itens: ResumoAtivo[] }) {
  return (
    <ul className="divide-y divide-line">
      {itens.map((a) => (
        <li key={a.ticker}>
          <Link href={`/ativo/${a.ticker}`} className="-mx-2 flex items-center gap-3 rounded-lg px-2 py-2.5 text-sm hover:bg-raised">
            <span className={`h-2 w-2 shrink-0 rounded-full ${a.variacao_dia >= 0 ? "bg-up" : "bg-down"}`} />
            <span className="min-w-0 flex-1">
              <span className="block font-semibold">{a.ticker}</span>
              <span className="block truncate text-xs text-muted">{a.nome}</span>
            </span>
            <span className="text-right">
              <span className="block font-medium">{fmtPreco(a.cotacao, a.moeda)}</span>
              <span className="block text-xs">{fmtSinal(a.variacao_dia)}</span>
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
