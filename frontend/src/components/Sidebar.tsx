"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Activity, Bot, BookOpen, Calculator, Landmark, Menu, Newspaper, Search, X } from "lucide-react";
import { API_URL } from "@/lib/api";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

const GRUPOS = [
  {
    titulo: "Mercado",
    itens: [
      { href: "/dashboard", label: "Visão geral", icon: Activity },
      { href: "/radar-noticias", label: "Radar de notícias", icon: Newspaper },
    ],
  },
  {
    titulo: "Análises",
    itens: [
      { href: "/preco-teto", label: "Preço-teto", icon: Calculator },
      { href: "/ativo/BBAS3", label: "Dossiê do ativo", icon: Search, prefixo: "/ativo" },
      { href: "/renda-fixa", label: "LCI, LCA e CDB", icon: Landmark },
    ],
  },
  {
    titulo: "Copiloto",
    itens: [{ href: "/analista-ia", label: "Analista IA", icon: Bot }],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const [aberto, setAberto] = useState(false);

  const nav = (
    <nav className="flex flex-col gap-5" aria-label="Páginas">
      {GRUPOS.map((g) => (
        <div key={g.titulo}>
          <p className="mb-1.5 px-3 text-xs text-muted">{g.titulo}</p>
          <div className="flex flex-col gap-0.5">
            {g.itens.map(({ href, label, icon: Icon, prefixo }) => {
              const ativo = pathname.startsWith(prefixo ?? href);
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setAberto(false)}
                  aria-current={ativo ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-xl px-3 py-2 text-[14px] transition-colors ${
                    ativo ? "bg-raised font-semibold text-text" : "text-muted hover:bg-raised/70 hover:text-text"
                  }`}
                >
                  <Icon size={16} strokeWidth={ativo ? 2.2 : 1.8} className={ativo ? "text-brand" : ""} />
                  {label}
                </Link>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );

  const marca = (
    <Link href="/dashboard" className="flex items-center gap-2.5">
      <Logo size={30} />
      <span className="leading-tight">
        <span className="wide block text-[15px] font-semibold">
          alpharadar<span className="text-muted">.b3</span>
        </span>
        <span className="block text-[11px] text-muted">Bolsa, FIIs e renda fixa</span>
      </span>
    </Link>
  );

  return (
    <>
      <aside className="card sticky top-3 hidden h-[calc(100vh-1.5rem)] w-[236px] shrink-0 flex-col p-3 lg:flex">
        <div className="mb-6 px-2 pt-1">{marca}</div>
        {nav}
        <div className="mt-auto flex flex-col gap-0.5 border-t border-line pt-3">
          <a
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-xl px-3 py-2 text-[14px] text-muted hover:bg-raised/70 hover:text-text"
          >
            <BookOpen size={16} strokeWidth={1.8} /> Documentação da API
          </a>
          <ThemeToggle />
          <p className="px-3 pt-2 text-[11px] leading-relaxed text-muted">
            Projeto educativo. Não é recomendação de investimento.
          </p>
        </div>
      </aside>

      <div className="card flex items-center justify-between px-4 py-3 lg:hidden">
        {marca}
        <button
          onClick={() => setAberto((v) => !v)}
          className="rounded-lg p-2 text-muted hover:bg-raised"
          aria-label={aberto ? "Fechar menu" : "Abrir menu"}
          aria-expanded={aberto}
        >
          {aberto ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      {aberto && (
        <div className="card px-3 pb-3 pt-2 lg:hidden">
          {nav}
          <div className="mt-3 border-t border-line pt-2">
            <ThemeToggle />
          </div>
        </div>
      )}
    </>
  );
}
