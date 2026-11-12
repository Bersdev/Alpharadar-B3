import type { NextConfig } from "next";

// Origem da API (a única de terceiros que o navegador pode contatar). Vem da mesma variável que o código usa.
const ORIGEM_API = (() => {
  try {
    return new URL(process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").origin;
  } catch {
    return "http://localhost:8000";
  }
})();

const producao = process.env.NODE_ENV === "production";

// Política de segurança de conteúdo (CSP).
//  - Em produção: tudo só de si mesmo, mais a API. O Next.js injeta scripts inline na hidratação, então
//    script-src precisa de 'unsafe-inline' (usar nonce exigiria renderização dinâmica de todas as páginas);
//    ainda assim a política bloqueia scripts, estilos, imagens e conexões vindos de outros domínios.
//  - Em desenvolvimento: só as diretivas que não atrapalham o hot reload (que usa eval e websocket).
const CSP = producao
  ? [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      `connect-src 'self' ${ORIGEM_API}`,
      "frame-src 'none'",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "object-src 'none'",
      "form-action 'self'",
    ].join("; ")
  : "frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'";

const CABECALHOS_SEGURANCA = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Content-Security-Policy", value: CSP },
];

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
  async headers() {
    return [{ source: "/:path*", headers: CABECALHOS_SEGURANCA }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
