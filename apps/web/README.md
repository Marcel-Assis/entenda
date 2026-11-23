# Base web do Entenda

Aplicação Next.js com TypeScript e página inicial em português do Brasil.
O primeiro build é estático e pode ser testado com Node.js 24 e pnpm 11.25.0.

A partir de `apps/web`, instale e valide:

```sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
```

Para desenvolvimento use `pnpm dev`. Para verificar o build localmente use
`pnpm start` e consulte `/`, que deve responder HTTP 200 com o título
Entenda. Uma rota desconhecida deve responder HTTP 404.

A conexão com um banco e as páginas públicas de proposições e fontes
dependem de uma interface de leitura aprovada.
