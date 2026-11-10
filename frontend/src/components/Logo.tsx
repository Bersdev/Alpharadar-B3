// Marca do AlphaRadar: uma tela de radar com varredura (SVG autoral).
export function Logo({ size = 30 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <circle cx="16" cy="16" r="14.5" fill="none" stroke="var(--line)" strokeWidth="1.5" />
      <circle cx="16" cy="16" r="9" fill="none" stroke="var(--line)" strokeWidth="1.2" />
      <circle cx="16" cy="16" r="3.5" fill="none" stroke="var(--line)" strokeWidth="1.2" />
      <g className="radar-sweep">
        <path d="M16 16 L16 1.5 A14.5 14.5 0 0 1 28.6 9 Z" fill="var(--brand)" opacity="0.28" />
        <line x1="16" y1="16" x2="16" y2="1.5" stroke="var(--brand)" strokeWidth="1.6" strokeLinecap="round" />
      </g>
      <circle cx="22.5" cy="10" r="1.8" fill="var(--brand)" />
      <circle cx="9.5" cy="21" r="1.3" fill="var(--up)" />
    </svg>
  );
}
