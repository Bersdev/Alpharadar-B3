"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { GLOSSARIO, type Termo } from "@/lib/glossario";
import { Disclaimer, Icon3D, PageHeader, Panel } from "@/components/ui";

const PASSOS = [
  { titulo: "Entenda o cenário", href: "/mercado", acao: "Abrir o mercado global",
    texto: "Veja se o dia é de busca por risco ou de proteção, como estão juros e dólar e o que a agenda traz. Cenário ruim não proíbe comprar, mas explica quedas e pede mais margem." },
  { titulo: "Defina o que você exige", href: "/preco-teto", acao: "Abrir o preço-teto",
    texto: "Escolha o dividend yield mínimo que faz sentido para você. Quanto mais alto o yield exigido, mais baixo o preço-teto: o ajuste dos controles é a sua régua." },
  { titulo: "Filtre por critérios", href: "/preco-teto", acao: "Filtrar ativos",
    texto: "Use margem mínima, dividend yield, ROE e setor para reduzir o universo a poucas ideias. O objetivo é tirar ruído, não achar a resposta pronta." },
  { titulo: "Leia o dossiê do ativo", href: "/ativo/BBAS3", acao: "Ver um exemplo",
    texto: "Confira o histórico, o endividamento, a volatilidade, a maior queda e as notícias. Pergunte: eu manteria isso se caísse 30%?" },
  { titulo: "Compare com a renda fixa", href: "/renda-fixa", acao: "Simular LCI, LCA e CDB",
    texto: "Com juro real alto, a renda fixa isenta é uma concorrente forte. A ação ou o FII precisa compensar o risco com um retorno projetado bem maior." },
  { titulo: "Decida e acompanhe", href: "/carteira", acao: "Abrir a carteira",
    texto: "A decisão final é sua. Registre o que comprou, acompanhe dividendos e revise as premissas a cada balanço, sem agir por notícia isolada." },
];

const CUIDADOS = [
  "Os preços-teto dependem de premissas (crescimento, payout, yield exigido). Teste cenários conservadores: se só funciona no cenário otimista, não tem margem de verdade.",
  "O método de Bazin foi pensado para empresas pagadoras de dividendos. Empresas de crescimento, como Nvidia e Amazon, reinvestem o lucro e aparecem \"caras\" por esse critério sem serem ruins.",
  "Margem positiva é um critério entre vários. Preço baixo pode refletir um problema real: prejuízo, dívida alta ou queda esperada do lucro (a famosa \"armadilha de valor\").",
  "Os fundamentos vêm do Yahoo Finance e dos balanços já publicados; erros e atrasos existem. Confirme no relatório da empresa antes de tomar uma decisão importante.",
  "Dividendos passados não garantem dividendos futuros. Yield muito alto, em geral, é sinal de preço caído e merece investigação.",
  "Efeito manada e emoção são os maiores inimigos do investidor: decida com critérios definidos antes da queda ou da euforia.",
];

export default function AprenderPage() {
  const [busca, setBusca] = useState("");
  const termos = useMemo(() => {
    const q = busca.trim().toLowerCase();
    const todos = Object.entries(GLOSSARIO) as [string, Termo][];
    return todos.filter(([, t]) => !q || `${t.nome} ${t.curto} ${t.longo}`.toLowerCase().includes(q));
  }, [busca]);
  const grupos = useMemo(() => {
    const m = new Map<string, [string, Termo][]>();
    termos.forEach((e) => m.set(e[1].grupo, [...(m.get(e[1].grupo) ?? []), e]));
    return [...m.entries()];
  }, [termos]);

  return (
    <>
      <PageHeader
        icon="gem"
        title="Aprenda a ler os números"
        description="Um caminho simples para decidir com convicção, e o que cada indicador do AlphaRadar significa."
      />

      <Panel title="Seis passos para decidir com mais convicção" className="mb-4">
        <p className="mb-5 max-w-3xl text-sm leading-relaxed text-muted">
          O maior problema do investidor hoje não é falta de informação, e sim excesso. Sem critérios, surgem a paralisia, o efeito manada e a decisão
          emocional. A ideia aqui é filtrar o que importa e deixar a decisão final com você.
        </p>
        <ol className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {PASSOS.map((p, i) => (
            <li key={p.titulo} className="rounded-2xl border border-line bg-raised/50 p-4">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-brand text-sm font-semibold text-white">{i + 1}</span>
              <h3 className="mt-3 font-semibold">{p.titulo}</h3>
              <p className="mt-1 text-sm leading-relaxed text-muted">{p.texto}</p>
              <Link href={p.href} className="mt-3 inline-block text-sm font-medium text-brand hover:underline">{p.acao}</Link>
            </li>
          ))}
        </ol>
      </Panel>

      <div className="mb-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <Panel title="Juros e bolsa: por que andam em sentido contrário">
          <div className="space-y-3 text-sm leading-relaxed text-muted">
            <p>
              <strong className="text-text">Juros sobem:</strong> a renda fixa paga mais, o crédito encarece e o lucro futuro das empresas vale menos hoje. Capital estrangeiro
              também tem uma alternativa segura mais bem paga (os títulos do governo americano). Resultado comum: bolsa pressionada, principalmente empresas endividadas, de crescimento e fundos de tijolo.
            </p>
            <p>
              <strong className="text-text">Juros caem:</strong> a renda fixa perde atratividade e o dinheiro procura retorno em ações e FIIs. Bancos e seguradoras ganham
              menos com a taxa, mas o consumo e o crédito melhoram.
            </p>
            <p>
              É uma tendência, não uma lei: lucros, política fiscal e humor global também mexem na bolsa. Acompanhe o gráfico de juros × Ibovespa e as expectativas do Focus em{" "}
              <Link href="/mercado" className="font-medium text-brand hover:underline">Mercado global</Link>.
            </p>
          </div>
        </Panel>
        <Panel title="Cuidados com o método">
          <ul className="space-y-2.5 text-sm leading-relaxed text-muted">
            {CUIDADOS.map((c) => (
              <li key={c} className="flex gap-2"><span className="text-warn">!</span> {c}</li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-3 text-lg font-semibold">
          <Icon3D name="search" size={40} /> Glossário
        </h2>
        <label className="relative w-full sm:w-72">
          <span className="sr-only">Buscar termo</span>
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
          <input value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Buscar: yield, payout, P/L…"
            className="w-full rounded-xl border border-line bg-surface py-2 pl-9 pr-3 text-sm placeholder:text-muted" />
        </label>
      </div>

      {grupos.length === 0 && <p className="py-10 text-center text-muted">Nenhum termo encontrado. Tente outra palavra.</p>}
      <div className="flex flex-col gap-4">
        {grupos.map(([grupo, lista]) => (
          <Panel key={grupo} title={grupo}>
            <dl className="grid gap-x-8 gap-y-5 md:grid-cols-2">
              {lista.map(([chave, t]) => (
                <div key={chave} id={chave}>
                  <dt className="font-semibold">{t.nome}</dt>
                  <dd className="mt-1 text-sm leading-relaxed text-muted">
                    {t.curto}
                    <span className="mt-1 block">{t.longo}</span>
                    {t.formula && <span className="mt-2 block rounded-lg bg-raised px-3 py-1.5 text-xs text-text">{t.formula}</span>}
                  </dd>
                </div>
              ))}
            </dl>
          </Panel>
        ))}
      </div>
      <Disclaimer />
    </>
  );
}
