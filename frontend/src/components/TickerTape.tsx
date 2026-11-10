"use client";

import Link from "next/link";
import { fmtNum, type Overview } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { Delta } from "./ui";

/** Faixa rolante com cotações e indicadores macro vindos do backend Python. */
export function TickerTape() {
  const { data } = useApi<Overview>("/api/overview");
  if (!data) {
    return <div className="h-9 border-b border-line bg-surface/40" aria-hidden="true" />;
  }
  const m = data.macro;
  const itens = [
    { label: "Ibovespa", valor: fmtNum(m.ibovespa, 0), var: m.ibovespa_var },
    { label: "Dólar", valor: `R$ ${fmtNum(m.dolar)}`, var: m.dolar_var },
    { label: "Selic", valor: `${fmtNum(m.selic_anual)}%`, var: null },
    { label: "CDI", valor: `${fmtNum(m.cdi_anual)}%`, var: null },
    { label: "IPCA 12m", valor: `${fmtNum(m.ipca_12m)}%`, var: null },
    ...data.ticker_tape.map((a) => ({ label: a.ticker, valor: fmtNum(a.cotacao), var: a.variacao_dia, href: `/ativo/${a.ticker}` })),
  ];
  const linha = (chave: string) =>
    itens.map((i) => {
      const conteudo = (
        <>
          <span className="font-semibold text-text">{i.label}</span>
          <span className="text-muted">{i.valor}</span>
          {i.var != null && <Delta value={i.var} />}
        </>
      );
      return "href" in i && i.href ? (
        <Link key={chave + i.label} href={i.href} className="flex items-center gap-2 px-4 hover:text-brand" tabIndex={-1}>
          {conteudo}
        </Link>
      ) : (
        <span key={chave + i.label} className="flex items-center gap-2 px-4">
          {conteudo}
        </span>
      );
    });

  return (
    <div className="overflow-hidden border-b border-line bg-surface/40 text-[13px]" aria-label="Cotações em destaque">
      {/* Conteúdo duplicado para a rolagem infinita sem "salto". */}
      <div className="tape-track flex w-max whitespace-nowrap py-2">
        {linha("a")}
        <span aria-hidden="true" className="flex">{linha("b")}</span>
      </div>
    </div>
  );
}
