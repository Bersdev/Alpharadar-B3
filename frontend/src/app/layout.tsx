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

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="pt-BR" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full">
        <div className="flex min-h-screen flex-col lg:flex-row">
          {/* Sidebar e topbar leem a URL (usePathname): o Suspense mantém o resto pré-renderizado. */}
          <Suspense fallback={<div className="hidden w-[248px] shrink-0 border-r border-line lg:block" />}>
            <Sidebar />
          </Suspense>
          <div className="flex min-w-0 flex-1 flex-col">
            <Suspense fallback={<div className="h-14 border-b border-line" />}>
              <Topbar />
            </Suspense>
            <TickerTape />
            <main className="mx-auto w-full max-w-[1280px] flex-1 px-4 py-8 md:px-8">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
