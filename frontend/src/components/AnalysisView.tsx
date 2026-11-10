// Exibe a resposta do copiloto (motor de regras em Python ou Claude).
import { Bot, Cpu } from "lucide-react";
import { nomeIA, type RespostaIA } from "@/lib/api";
import { TickerChip } from "./ui";

/** Renderizador mínimo de markdown: parágrafos, listas "- " e **negrito**. */
function TextoLLM({ texto }: { texto: string }) {
  const blocos = texto.split(/\n{2,}/);
  const negrito = (linha: string) =>
    linha.split(/(\*\*[^*]+\*\*)/g).map((parte, i) =>
      parte.startsWith("**") ? <strong key={i}>{parte.slice(2, -2)}</strong> : <span key={i}>{parte}</span>,
    );
  return (
    <div className="flex flex-col gap-3 text-[15px] leading-relaxed">
      {blocos.map((b, i) => {
        const linhas = b.split("\n").filter(Boolean);
        if (linhas.every((l) => /^\s*[-*] /.test(l))) {
          return (
            <ul key={i} className="ml-5 list-disc space-y-1">
              {linhas.map((l, j) => <li key={j}>{negrito(l.replace(/^\s*[-*] /, ""))}</li>)}
            </ul>
          );
        }
        if (/^#{1,4} /.test(b)) return <h4 key={i} className="font-semibold">{b.replace(/^#+ /, "")}</h4>;
        return <p key={i}>{negrito(b)}</p>;
      })}
    </div>
  );
}

export function AnalysisView({ r }: { r: RespostaIA }) {
  return (
    <article className="flex flex-col gap-5">
      <div>
        <div className="mb-2 flex items-center gap-2 text-xs text-muted">
          {r.modo === "llm" ? <Bot size={14} className="text-brand" /> : <Cpu size={14} className="text-brand" />}
          {r.modo === "llm" ? `Análise redigida pelo ${nomeIA(r.provedor)} com números do motor Python` : "Motor de regras em Python (sem IA paga)"}
        </div>
        <h3 className="wide text-xl font-semibold">{r.titulo}</h3>
        <p className="mt-2 max-w-3xl leading-relaxed text-muted">{r.resumo}</p>
        {r.ativos.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {r.ativos.map((t) => <TickerChip key={t} ticker={t} />)}
          </div>
        )}
      </div>

      {r.texto_llm && (
        <div className="rounded-lg border border-brand/30 bg-brand-soft/40 p-4">
          <TextoLLM texto={r.texto_llm} />
        </div>
      )}
      {r.aviso_llm && <p className="text-sm text-brand">{r.aviso_llm}</p>}

      <div className="grid gap-x-8 gap-y-5 md:grid-cols-2">
        {r.secoes.map((s) => (
          <section key={s.titulo}>
            <h4 className="mb-2 border-b border-line pb-1.5 text-sm font-semibold">{s.titulo}</h4>
            <ul className="space-y-1.5 text-sm leading-relaxed text-muted">
              {s.itens.map((item, i) => (
                <li key={i} className="pl-3 [text-indent:-0.75rem]">
                  <span className="text-brand">›</span> {item}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <p className="text-xs text-muted">{r.aviso}</p>
    </article>
  );
}
