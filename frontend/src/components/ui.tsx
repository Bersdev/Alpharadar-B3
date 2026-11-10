// Peças visuais reutilizadas em todas as páginas.
import Link from "next/link";
import { AlertTriangle, Loader2, WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { fmtSinal, type Fonte } from "@/lib/api";

export function PageHeader({ title, description, aside }: { title: string; description: string; aside?: ReactNode }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        <h1 className="wide text-2xl font-semibold text-text md:text-[1.75rem] md:leading-tight">{title}</h1>
        <p className="mt-1.5 text-[14px] leading-relaxed text-muted">{description}</p>
      </div>
      {aside}
    </header>
  );
}

export function Panel({
  title,
  children,
  className = "",
  action,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
  action?: ReactNode;
}) {
  return (
    <section className={`rounded-2xl border border-line bg-surface p-5 ${className}`}>
      {(title || action) && (
        <div className="mb-4 flex items-center justify-between gap-3">
          {title && <h2 className="text-[15px] font-semibold text-text">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

/** Variação colorida: verde-mar na alta, coral na baixa. */
export function Delta({ value, className = "" }: { value: number | null | undefined; className?: string }) {
  const cor = value == null || value === 0 ? "text-muted" : value > 0 ? "text-up" : "text-down";
  return <span className={`font-medium ${cor} ${className}`}>{fmtSinal(value)}</span>;
}

const TONS = {
  up: "bg-up/10 text-up",
  down: "bg-down/10 text-down",
  warn: "bg-warn/10 text-warn",
  brand: "bg-brand/15 text-brand",
  muted: "bg-raised text-muted",
} as const;

/** Pílula de status, como "Pago" ou "No prazo" nos cartões do quadro. */
export function Pill({ tone = "muted", children }: { tone?: keyof typeof TONS; children: ReactNode }) {
  return <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium ${TONS[tone]}`}>{children}</span>;
}

export function SourceBadge({ fonte }: { fonte: Fonte | undefined }) {
  if (!fonte || fonte === "ao_vivo") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-md bg-up/10 px-2.5 py-1 text-xs text-up">
        <span className="h-1.5 w-1.5 rounded-full bg-up" /> Dados ao vivo
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-md bg-warn/10 px-2.5 py-1 text-xs text-warn"
      title="Yahoo Finance ou Banco Central indisponíveis: exibindo dados locais de demonstração."
    >
      <WifiOff size={12} /> {fonte === "misto" ? "Parte offline" : "Modo offline"}
    </span>
  );
}

export function TickerChip({ ticker, efeito }: { ticker: string; efeito?: "beneficiado" | "prejudicado" }) {
  const cor =
    efeito === "beneficiado"
      ? "border-up/40 text-up hover:bg-up/10"
      : efeito === "prejudicado"
        ? "border-down/40 text-down hover:bg-down/10"
        : "border-line text-text hover:bg-raised";
  return (
    <Link
      href={`/ativo/${ticker}`}
      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-semibold ${cor}`}
      title={efeito ? `${ticker} — ${efeito}` : ticker}
    >
      {efeito === "beneficiado" ? "▲ " : efeito === "prejudicado" ? "▼ " : ""}
      {ticker}
    </Link>
  );
}

export function Loading({ label = "Buscando dados no motor Python" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-16 text-muted" role="status">
      <Loader2 className="animate-spin text-brand" size={18} /> {label}…
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-2xl border border-down/40 bg-down/5 p-5 text-sm" role="alert">
      <div className="flex items-center gap-2 font-semibold text-down">
        <AlertTriangle size={16} /> Backend indisponível
      </div>
      <p className="max-w-xl text-muted">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="rounded-md bg-raised px-3 py-1.5 text-text hover:bg-line">
          Tentar novamente
        </button>
      )}
    </div>
  );
}

export function ScorePill({ total, classificacao }: { total: number; classificacao?: string }) {
  const cor = total >= 65 ? "text-up border-up/40" : total >= 50 ? "text-brand border-brand/40" : "text-down border-down/40";
  return (
    <span className={`inline-flex items-baseline gap-1 rounded-md border px-2 py-0.5 ${cor}`} title={classificacao}>
      <span className="text-sm font-semibold">{Math.round(total)}</span>
      <span className="text-[10px] opacity-70">/100</span>
    </span>
  );
}

export const Disclaimer = () => (
  <p className="mt-10 border-t border-line pt-4 text-xs text-muted">
    Conteúdo educativo calculado a partir de dados públicos e premissas simplificadas. Não é recomendação de investimento.
  </p>
);
