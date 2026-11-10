import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Suspense } from "react";
import { Sidebar } from "@/components/Sidebar";
import { Topbar } from "@/components/Topbar";
import { TickerTape } from "@/components/TickerTape";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AlphaRadar B3",
  description: "Preço-teto, Score Alpha, renda fixa e radar de notícias da bolsa brasileira — motor em Python.",
};

// Roda antes da primeira pintura: aplica o tema salvo (ou o do sistema) e evita o "piscar" claro/escuro.
const SCRIPT_TEMA = `(function(){try{var t=localStorage.getItem("alpharadar-tema");if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="light"}})();`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${inter.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body className="min-h-full">
        <div className="flex min-h-screen flex-col gap-3 p-3 lg:flex-row">
          {/* Sidebar e topbar leem a URL (usePathname): o Suspense mantém o resto pré-renderizado. */}
          <Suspense fallback={<div className="hidden w-[236px] shrink-0 lg:block" />}>
            <Sidebar />
          </Suspense>
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <Suspense fallback={<div className="card h-14" />}>
              <Topbar />
            </Suspense>
            <TickerTape />
            <main className="mx-auto w-full max-w-[1280px] flex-1 px-1 py-4 md:px-3">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
