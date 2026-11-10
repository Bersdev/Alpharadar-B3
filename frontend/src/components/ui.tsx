// Peças visuais reutilizadas em todas as páginas.
import Image from "next/image";
import Link from "next/link";
import { AlertTriangle, HelpCircle, Loader2, Star, WifiOff } from "lucide-react";
import type { ReactNode } from "react";
import { fmtSinal, type Fonte } from "@/lib/api";
import { GLOSSARIO, type ChaveTermo } from "@/lib/glossario";
import { alternarFavorito, useFavoritos } from "@/lib/storage";

/** Ícone 3D decorativo (Fluent Emoji 3D, licença MIT). Os arquivos ficam em public/icons. */
export function Icon3D({ name, size = 72, className = "" }: { name: string; size?: number; className?: string }) {
  return (
    <Image
      src={`/icons/${name}.png`}
      alt=""
      aria-hidden="true"
      width={size}
      height={size}
      className={`icon3d pointer-events-none select-none ${className}`}
    />
  );
}

export function PageHeader({
  title,
  description,
  aside,
  icon,
}: {
  title: string;
  description: string;
  aside?: ReactNode;
  icon?: string;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
      <div className="flex items-center gap-4">
        {icon && <Icon3D name={icon} size={64} className="hidden sm:block" />}
        <div className="max-w-2xl">
          <h1 className="wide text-2xl font-semibold text-text md:text-[1.75rem] md:leading-tight">{title}</h1>
          <p className="mt-1 text-[14px] leading-relaxed text-muted">{description}</p>
        </div>
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
    <section className={`card p-5 ${className}`}>
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
    <div className="flex flex-col items-start gap-3 rounded-2xl border border-down/40 bg-down/10 p-5 text-sm" role="alert">
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

/** Ícone (?) que explica um termo ao passar o mouse ou focar com o teclado. O texto vem de lib/glossario.ts. */
export function InfoTip({ termo, className = "" }: { termo: ChaveTermo; className?: string }) {
  const t = GLOSSARIO[termo];
  return (
    <span className={`group relative inline-flex align-middle ${className}`}>
      <button
        type="button"
        aria-label={`O que é ${t.nome}`}
        className="grid h-4 w-4 place-items-center rounded-full text-muted hover:text-brand focus-visible:text-brand"
      >
        <HelpCircle size={14} />
      </button>
      <span
        role="tooltip"
        className="card pointer-events-none invisible absolute left-1/2 top-full z-30 mt-1.5 w-64 -translate-x-1/2 p-3 text-left text-xs font-normal leading-relaxed text-text opacity-0 transition-opacity group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100"
      >
        <span className="mb-1 block font-semibold">{t.nome}</span>
        {t.curto}
        {"formula" in t && t.formula && <span className="mt-1.5 block rounded-md bg-raised px-2 py-1 text-[11px] text-muted">{t.formula}</span>}
      </span>
    </span>
  );
}

/** Estrela para marcar um ativo como favorito (salvo no navegador). */
export function StarButton({ ticker, className = "" }: { ticker: string; className?: string }) {
  const favoritos = useFavoritos();
  const ativo = favoritos.includes(ticker);
  return (
    <button
      type="button"
      onClick={(e) => {
        e.preventDefault();
        e.stopPropagation();
        alternarFavorito(ticker);
      }}
      aria-pressed={ativo}
      aria-label={ativo ? `Remover ${ticker} dos favoritos` : `Adicionar ${ticker} aos favoritos`}
      title={ativo ? "Remover dos favoritos" : "Adicionar aos favoritos"}
      className={`grid h-7 w-7 place-items-center rounded-lg transition-colors hover:bg-raised ${ativo ? "text-warn" : "text-muted"} ${className}`}
    >
      <Star size={16} fill={ativo ? "currentColor" : "none"} strokeWidth={1.8} />
    </button>
  );
}

/** Selo de margem como no vídeo de referência: verde quando há margem de segurança, cinza quando não há. */
export function MargemBadge({ margem }: { margem: number | null | undefined }) {
  if (margem == null) return <Pill tone="muted">sem dividendos</Pill>;
  return margem > 0 ? <Pill tone="up">margem positiva</Pill> : <Pill tone="muted">sem margem</Pill>;
}
