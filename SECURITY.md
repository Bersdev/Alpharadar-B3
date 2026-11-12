# Segurança

## O que é público por desenho

O AlphaRadar B3 **não tem login nem dados de usuário no servidor**. Todas as rotas da API são públicas e somente
de leitura ou de cálculo: cotações, indicadores, simuladores e o analista de IA. Não existe rota que grave, altere ou
apague dados.

- **Favoritos e carteira** ficam apenas no `localStorage` do navegador de cada pessoa. O servidor nunca os recebe.
  Ao ler, o app valida o formato (ticker, números finitos e dentro de um limite) e descarta o que estiver corrompido.
- Quem chama a API direto (curl) não é barrado pelo CORS: ele só protege o navegador de quem visita o site.

## Defesas implementadas

| Ameaça | Defesa |
|---|---|
| Abuso e negação de serviço | Limite de pedidos **por IP** (IPv6 agrupado por /64, para girar de endereço não burlar): 180/min na API, 20/min nos simuladores e 8/min na IA. Só a IA tem teto **global** (60/min), porque protege a cota externa do provedor; nas demais rotas um teto global deixaria poucos endereços bloquearem todos os visitantes. Janela deslizante, memória limitada (pedido bloqueado não ocupa memória), resposta `429` com `Retry-After`. |
| Corpo de pedido gigante | Máximo de 16 KB (`413`) e `Content-Length` obrigatório nos POST (`411`). Campos com tamanho e faixa validados (Pydantic). |
| Custo de CPU por pedido | O simulador de renda fixa foi vetorizado: 360 meses caíram de ~460 ms para ~45 ms. |
| Memória e cache | Cache com tamanho máximo e **uma** busca por chave (vários pedidos simultâneos com cache frio não repetem as consultas lentas). |
| IP falsificado | Os cabeçalhos de IP só são lidos quando a conexão vem de um proxy interno (Railway); o `X-Real-IP` é sobrescrito pela plataforma. Visitante direto tem o cabeçalho ignorado. |
| Prompt injection na IA | A pergunta e as manchetes vão entre tags, sem `<` e `>`, com instruções de tratá-las só como informação. O modelo recebe números já calculados e não tem ferramentas. |
| Fontes externas maliciosas | Downloads com teto de 2 MB e só `http(s)`; RSS lido com `defusedxml` (sem XXE); links de notícias só `http(s)` (sem `javascript:`). |
| Vazamento de segredos | Chaves só em variáveis de ambiente; `.env` ignorado pelo Git; logs registram só o tipo do erro, nunca a mensagem (que pode conter URLs com chaves). Varredura automática no CI (`backend/scripts/verificar_segredos.py`). |
| Navegador | CSP restritiva em produção (só o próprio site e a API), `X-Frame-Options`, `nosniff`, HSTS, `Permissions-Policy` e `COOP`. |
| Cadeia de suprimentos | Dependências do backend com versão fixa; `pip-audit` e `npm audit` no CI; Dependabot semanal; ações do GitHub fixadas por hash e CI com permissão somente de leitura. |

## Limitações conhecidas

- O estado dos limites fica na memória de um processo. Com várias réplicas, cada uma conta separado (seria preciso Redis).
- A CSP mantém `'unsafe-inline'` em scripts e estilos, porque o Next.js injeta scripts inline; usar nonce exigiria
  renderização dinâmica de todas as páginas.
- `/docs` e `/openapi.json` ficam públicos (a API é aberta e o código também).

## Segredos

Chaves de API ficam só em variáveis de ambiente (`backend/.env` localmente, painel da Railway em produção).
O arquivo `.env` está no `.gitignore`; o `.env.example` traz apenas os nomes, sem valores. **Nunca** coloque chaves
em variáveis `NEXT_PUBLIC_*` do frontend: elas vão para o navegador de todos os visitantes. Antes de cada commit:

```bash
python backend/scripts/verificar_segredos.py
```

## Reportar uma vulnerabilidade

Abra um *Security Advisory* privado na aba **Security** deste repositório no GitHub (também listado em
`/.well-known/security.txt`), ou uma *issue* sem detalhes sensíveis pedindo contato. Não publique exploits antes de uma correção.
