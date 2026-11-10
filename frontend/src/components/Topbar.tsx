"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Search, Sparkles } from "lucide-react";
import { TICKERS } from "@/lib/tickers";

const TITULOS: Record<string, [string, string]> = {
  "/dashboard": ["Visão geral", "do mercado"],
  "/preco-teto": ["Preço-teto", "e projeção"],
  "/ativo": ["Dossiê", "do ativo"],
  "/renda-fixa": ["Renda fixa", "LCI, LCA e CDB"],
  "/radar-noticias": ["Radar", "de notícias"],
  "/analista-ia": ["Analista", "com IA"],
  "/mercado": ["Mercado", "global"],
  "/dividendos": ["Dividendos", "e renda passiva"],
  "/carteira": ["Minha", "carteira"],
  "/aprender": ["Aprender", "a ler os números"],
};

/** Barra superior em cartão: título da página, busca de ativo (Ctrl/⌘ + K) e atalho para o copiloto. */
export function Topbar() {
  const pathname = usePathname();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busca, setBusca] = useState("");
  const [aviso, setAviso] = useState(false);
  const rota = Object.keys(TITULOS).find((r) => pathname.startsWith(r));
  const [titulo, sufixo] = rota ? TITULOS[rota] : ["AlphaRadar", "B3"];

  useEffect(() => {
    const atalho = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", atalho);
    return () => window.removeEventListener("keydown", atalho);
  }, []);

  function buscar(e: FormEvent) {
    e.preventDefault();
    const t = busca.trim().toUpperCase();
    if ((TICKERS as readonly string[]).includes(t)) {
      setAviso(false);
      setBusca("");
      router.push(`/ativo/${t}`);
    } else {
      setAviso(true);
    }
  }

  return (
    <div className="card flex h-14 items-center justify-between gap-4 px-4 md:px-5">
      <h2 className="wide hidden shrink-0 text-xl font-semibold md:block">
        {titulo} <span className="text-muted">{sufixo}</span>
      </h2>

      <form onSubmit={buscar} className="relative min-w-0 flex-1 md:max-w-[340px] md:flex-none">
        <label htmlFor="busca-ativo" className="sr-only">
          Buscar ativo
        </label>
        <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
        <input
          id="busca-ativo"
          ref={inputRef}
          value={busca}
          onChange={(e) => {
            setBusca(e.target.value);
            setAviso(false);
          }}
          list="tickers-monitorados"
          placeholder="Buscar: PETR4, NVDA…"
          autoComplete="off"
          className="w-full rounded-xl border border-line bg-raised py-2 pl-9 pr-12 text-sm placeholder:text-muted"
        />
        <kbd className="pointer-events-none absolute right-2.5 top-1/2 hidden -translate-y-1/2 rounded border border-line px-1.5 py-0.5 text-[10px] text-muted sm:block">
          Ctrl K
        </kbd>
        <datalist id="tickers-monitorados">
          {TICKERS.map((t) => (
            <option key={t} value={t} />
          ))}
        </datalist>
        {aviso && (
          <p role="alert" className="card absolute left-0 top-full z-10 mt-1 px-3 py-1.5 text-xs text-muted">
            Ativo não monitorado. Escolha um da lista (B3 ou EUA).
          </p>
        )}
      </form>

      <Link
        href="/analista-ia"
        className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-brand px-3.5 py-2 text-sm font-medium text-white shadow-sm hover:brightness-110"
      >
        <Sparkles size={15} /> <span className="hidden sm:inline">Perguntar à IA</span>
      </Link>
    </div>
  );
}
