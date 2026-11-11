# Segurança

## O que é público por desenho

O AlphaRadar B3 **não tem login nem dados de usuário no servidor**. Todas as rotas da API são públicas e somente
de leitura ou de cálculo: cotações, indicadores, simuladores e o analista de IA. Não existe rota que grave, altere ou
apague dados.

- **Favoritos e carteira** ficam apenas no `localStorage` do navegador de cada pessoa. O servidor nunca os recebe.
- A rota de IA (`POST /api/ai/analyze`) é limitada: 8 perguntas por minuto por IP e 60 por minuto no total,
  para proteger a cota gratuita do provedor de IA.
- O CORS libera apenas o site da demonstração e o ambiente local. Isso protege o navegador de quem visita; quem chama
  a API direto continua podendo usá-la, como em qualquer API pública.

## Segredos

Chaves de API ficam só em variáveis de ambiente (`backend/.env` localmente, painel da Railway em produção).
O arquivo `.env` está no `.gitignore`; o `.env.example` traz apenas os nomes, sem valores. **Nunca** coloque chaves
em variáveis `NEXT_PUBLIC_*` do frontend: elas vão para o navegador de todos os visitantes.

## Reportar uma vulnerabilidade

Abra um *Security Advisory* privado na aba **Security** deste repositório no GitHub, ou uma *issue* sem detalhes
sensíveis pedindo contato. Não publique exploits antes de uma correção.
