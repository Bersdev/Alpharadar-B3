import { Suspense } from "react";
import { DossieAtivo } from "./DossieAtivo";
import { TICKERS } from "@/lib/tickers";
import { Loading } from "@/components/ui";

// Pré-renderiza a "casca" estática das 16 páginas; os dados vêm do backend no navegador.
export function generateStaticParams() {
  return TICKERS.map((ticker) => ({ ticker }));
}

export default function AtivoPage() {
  // useParams() lê a URL no navegador: a fronteira Suspense permite pré-renderizar o resto.
  return (
    <Suspense fallback={<Loading label="Abrindo dossiê" />}>
      <DossieAtivo />
    </Suspense>
  );
}
