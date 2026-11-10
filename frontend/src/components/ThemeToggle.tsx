"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";

type Tema = "light" | "dark";
const CHAVE = "alpharadar-tema";

function assinar(aviso: () => void) {
  window.addEventListener("alpharadar-tema", aviso);
  return () => window.removeEventListener("alpharadar-tema", aviso);
}
const lerTema = (): Tema => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");

function definirTema(t: Tema) {
  document.documentElement.dataset.theme = t;
  try {
    localStorage.setItem(CHAVE, t);
  } catch {
    /* armazenamento bloqueado: o tema vale só nesta visita */
  }
  window.dispatchEvent(new Event("alpharadar-tema"));
}

/** Seletor claro/escuro. O tema escuro é OLED (preto absoluto). A escolha fica salva no navegador. */
export function ThemeToggle() {
  const tema = useSyncExternalStore(assinar, lerTema, () => "light" as Tema);
  const botao = (t: Tema, rotulo: string, icone: React.ReactNode) => (
    <button
      type="button"
      onClick={() => definirTema(t)}
      aria-pressed={tema === t}
      aria-label={rotulo}
      title={rotulo}
      className={`grid h-7 w-8 place-items-center rounded-lg transition-colors ${
        tema === t ? "bg-surface text-text shadow-[var(--shadow)] ring-1 ring-line" : "text-muted hover:text-text"
      }`}
    >
      {icone}
    </button>
  );
  return (
    <div className="flex items-center justify-between rounded-xl px-3 py-1.5 text-[14px] text-muted">
      <span className="flex items-center gap-3">
        <Sun size={16} strokeWidth={1.8} /> Tema
      </span>
      <div className="flex gap-0.5 rounded-xl bg-raised p-0.5" role="group" aria-label="Tema do site">
        {botao("light", "Tema claro", <Sun size={14} />)}
        {botao("dark", "Tema escuro OLED", <Moon size={14} />)}
      </div>
    </div>
  );
}
