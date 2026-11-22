# Arquitetura inicial

**Status:** proposta de fundação, sujeita a validação com dados reais e restrições de custo.

## Componentes
- **Web:** Next.js + TypeScript, páginas responsivas e indexáveis.
- **Banco, autenticação e armazenamento:** PostgreSQL/Supabase, migrações e RLS.
- **Worker:** Python para coleta, normalização, reconciliação, detecção de eventos e preparação editorial.
- **Mobile:** React Native + Expo em fase posterior.
- **Monorepositório:** pnpm workspaces/Turborepo quando houver aplicações suficientes para justificar a configuração.

## Fluxo de dados
Fonte oficial → conector → registro bruto versionado → validação/normalização → reconciliação/deduplicação → entidades e eventos → pacote de evidências → rascunho assistido por IA → verificação → revisão humana → publicação versionada.

## Requisitos de ingestão
- Identificadores oficiais, URL de origem, timestamps de coleta e publicação, hash e versão.
- Paginação, checkpoints, retentativas, backoff, limites e tratamento de falhas parciais.
- Reprocessamento seguro, idempotência, histórico de alterações e quarentena de registros ambíguos.
- Diferenciar ausência de novidades de falha de coleta.
- Não tratar desaparecimento de registro como exclusão definitiva sem confirmação.

## Segurança e operação
- Credenciais de serviço apenas no servidor; autorização e RLS para dados privados.
- Painel administrativo protegido e auditável.
- Logs estruturados, alertas de falhas, acompanhamento de atualização das fontes.
- Backup e restauração testados antes do lançamento.
- Controle de custo de processamento e IA.

## Estrutura prevista
```text
apps/web/
apps/worker/
apps/mobile/                 # fase posterior
packages/domain/
packages/contracts/
packages/validation/
packages/api-client/
packages/design-tokens/
supabase/migrations/
docs/
.github/
```

As pastas previstas não devem ser confundidas com código implementado.
