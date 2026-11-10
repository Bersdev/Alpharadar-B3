"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Activity, Bot, BookOpen, Calculator, Landmark, Menu, Newspaper, Search, X } from "lucide-react";
import { API_URL } from "@/lib/api";
import { Logo } from "./Logo";

const GRUPOS = [
  {
    titulo: "Mercado",
    itens: [
      { href: "/dashboard", label: "Pulso do mercado", icon: Activity },
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
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-[14px] ${
                    ativo ? "bg-raised font-medium text-text" : "text-muted hover:bg-raised/60 hover:text-text"
                  }`}
                >
                  <Icon size={16} strokeWidth={1.8} className={ativo ? "text-brand" : ""} />
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
      <Logo size={26} />
      <span className="wide text-[17px] font-semibold">
        alpharadar<span className="text-muted">.b3</span>
      </span>
    </Link>
  );

  return (
    <>
      <aside className="sticky top-0 hidden h-screen w-[248px] shrink-0 flex-col border-r border-line bg-surface px-3 py-5 lg:flex">
        <div className="mb-7 px-3">{marca}</div>
        {nav}
        <div className="mt-auto flex flex-col gap-1">
          <a
            href={`${API_URL}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-[14px] text-muted hover:bg-raised/60 hover:text-text"
          >
            <BookOpen size={16} strokeWidth={1.8} /> Documentação da API
          </a>
          <p className="px-3 pt-2 text-[11px] leading-relaxed text-muted">
            Motor financeiro em Python. Projeto educativo, sem recomendação de investimento.
          </p>
        </div>
      </aside>

      <div className="flex items-center justify-between border-b border-line bg-surface px-4 py-3 lg:hidden">
        {marca}
        <button
          onClick={() => setAberto((v) => !v)}
          className="rounded-md p-2 text-muted hover:bg-raised"
          aria-label={aberto ? "Fechar menu" : "Abrir menu"}
          aria-expanded={aberto}
        >
          {aberto ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      {aberto && <div className="border-b border-line bg-surface px-3 pb-4 lg:hidden">{nav}</div>}
    </>
  );
}
