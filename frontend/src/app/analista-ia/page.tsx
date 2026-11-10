"use client";

import { useState, type FormEvent } from "react";
import { Loader2, SendHorizontal } from "lucide-react";
import { api, nomeIA, type RespostaIA } from "@/lib/api";
import { useApi } from "@/lib/useApi";
import { AnalysisView } from "@/components/AnalysisView";
import { Disclaimer, ErrorState, PageHeader, Panel } from "@/components/ui";

const SUGESTOES = [
  "Avalie o histórico e o risco de BBAS3",
  "Quais empresas da bolsa ganham com a alta da Selic?",
  "Compare LCI 92% do CDI com o FII HGLG11",
  "E se a Selic cair, quem se beneficia?",
  "Panorama do mercado e melhores Score Alpha",
];

export default function AnalistaIAPage() {
  const [pergunta, setPergunta] = useState("");
  const [historico, setHistorico] = useState<RespostaIA[]>([]);
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const { data: saude } = useApi<{ ia_generativa: boolean; ia_provedor: string | null }>("/api/health");

  async function perguntar(texto: string) {
    const q = texto.trim();
    if (!q || carregando) return;
    setCarregando(true);
    setErro(null);
    setPergunta(q);
    try {
      const r = await api<RespostaIA>("/api/ai/analyze", { pergunta: q });
      setHistorico((h) => [r, ...h].slice(0, 6));
      setPergunta("");
    } catch (e) {
      setErro(e instanceof Error ? e.message : String(e));
    } finally {
      setCarregando(false);
    }
  }

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    void perguntar(pergunta);
  };

  return (
    <>
      <PageHeader
        icon="robot"
        title="Analista IA"
        description="Pergunte sobre risco, histórico, efeito dos juros ou compare renda fixa com ações e FIIs. As contas são feitas pelo motor Python; a IA só interpreta os números."
        aside={saude && (
          <span className="rounded-full border border-line px-3 py-1 text-xs text-muted">
            {saude.ia_generativa ? `${nomeIA(saude.ia_provedor)} conectado` : "Motor de regras em Python (sem chave de IA)"}
          </span>
        )}
      />

      <Panel>
        <form onSubmit={enviar} className="flex gap-2">
          <label htmlFor="pergunta" className="sr-only">
            Sua pergunta
          </label>
          <input
            id="pergunta"
            value={pergunta}
            onChange={(e) => setPergunta(e.target.value)}
            placeholder="Ex.: Avalie o histórico e o risco de TAEE11"
            maxLength={1000}
            className="min-w-0 flex-1 rounded-xl border border-line bg-raised px-4 py-3 text-[15px] text-text placeholder:text-muted"
          />
          <button
            type="submit"
            disabled={carregando || !pergunta.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 font-semibold text-white hover:brightness-110 disabled:opacity-50"
          >
            {carregando ? <Loader2 size={16} className="animate-spin" /> : <SendHorizontal size={16} />}
            <span className="hidden sm:inline">Perguntar</span>
          </button>
        </form>
        <div className="mt-4 flex flex-wrap gap-2">
          {SUGESTOES.map((s) => (
            <button
              key={s}
              onClick={() => perguntar(s)}
              disabled={carregando}
              className="rounded-full border border-line px-3 py-1.5 text-sm text-muted hover:border-brand/50 hover:text-text disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      </Panel>

      <div className="mt-6 flex flex-col gap-6">
        {erro && <ErrorState message={erro} />}
        {carregando && (
          <p className="flex items-center gap-2 text-sm text-muted" role="status">
            <Loader2 size={15} className="animate-spin text-brand" /> Calculando: {pergunta}
          </p>
        )}
        {historico.length === 0 && !carregando && !erro && (
          <p className="py-10 text-center text-muted">Escolha uma sugestão acima ou escreva sua pergunta para começar.</p>
        )}
        {historico.map((r, i) => (
          <Panel key={`${r.pergunta}-${historico.length - i}`} className={i > 0 ? "opacity-80" : ""}>
            <p className="mb-4 text-sm text-muted">
              Você perguntou: <span className="text-text">{r.pergunta}</span>
            </p>
            <AnalysisView r={r} />
          </Panel>
        ))}
      </div>
      <Disclaimer />
    </>
  );
}
