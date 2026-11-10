# AlphaRadar B3 — Frontend

Dashboard em Next.js 16 (App Router) + TypeScript + Tailwind CSS 4 + Recharts.

```bash
npm install
npm run dev     # http://localhost:3000
```

O frontend consome a API Python em `http://localhost:8000` (altere com a variável `NEXT_PUBLIC_API_URL`). Inicie o backend antes: veja o [README principal](../README.md).

| Pasta | Conteúdo |
|---|---|
| `src/app/` | As 6 páginas: `dashboard`, `preco-teto`, `ativo/[ticker]`, `renda-fixa`, `radar-noticias`, `analista-ia` |
| `src/components/` | Sidebar, ticker tape, gráficos (Recharts), visualização da análise de IA e peças de UI |
| `src/lib/api.ts` | Cliente HTTP, tipos das respostas e formatação pt-BR |
