# Integração e entrega contínuas

O workflow [Worker CI](../.github/workflows/worker-ci.yml) executa em PRs,
em pushes para `main` e sob demanda. O job **Worker and PostgreSQL**
instala as dependências em Python 3.12, verifica whitespace com Git e Ruff,
executa lint, audita dependências com pip-audit, aplica todas as migrações
em PostgreSQL 17 descartável e roda as suítes SQL e Python. Os testes não
dependem da API oficial em tempo real.

O workflow usa `pull_request`, token de leitura, checkout sem credenciais
persistentes e revisões fixas para actions e imagem. As credenciais do
PostgreSQL de teste são dispensadas porque o serviço é descartável e fica
no runner hospedado. Não use esse mecanismo em banco compartilhado.
A auditoria Python depende do catálogo de vulnerabilidades e não cobre
a imagem ou bibliotecas de sistema embarcadas. Um resultado sem alertas
vale para as dependências e a base consultadas naquela execução.

## Fluxo de integração

1. Verifique as issues, o acompanhamento do projeto e os PRs. Crie uma
   branch específica a partir de `main` atualizada ou da branch que fornece
   a dependência imediata. Abra o PR contra essa base e indique a cadeia no
   resumo, com os testes executados e os pendentes.
2. Revise os PRs em ordem de dependência. Os PRs #6–#9 foram integrados
   em branches intermediárias. A branch `integration/worker-ci` reúne
   o worker, as migrações e a CI contra a `main` `4055103`. As auditorias,
   o modelo documental e o acompanhamento já estão na `main`.
3. Antes de tornar a CI obrigatória globalmente, integre o worker e
   confirme o check em um PR representativo contra `main`. O job exige
   os arquivos do worker e das migrações. Privilégios e regras do GitHub
   ficam sujeitos à aprovação do proprietário.

## Proteção proposta para main

O proprietário deve avaliar em **Settings → Rules → Rulesets** a aplicação
das seguintes regras, após a primeira execução confirmada no GitHub:

- Exigir PR, uma aprovação independente, invalidação de aprovações obsoletas
  após novos commits e resolução de conversas.
- Exigir o check **Worker and PostgreSQL** emitido pelo GitHub Actions.
  Selecione o contexto exato que aparecer após a primeira execução.
  Exigir branch atualizada antes de merge.
- Bloquear push direto, force push e exclusão da branch. Restringir bypass.
- Exigir revisão por responsáveis definidos pelo proprietário via CODEOWNERS
  para áreas sensíveis. A configuração depende de confirmar quais contas
  têm permissão de revisão no repositório.

### Auto-merge proposto

Se o proprietário habilitar o recurso, um mantenedor poderá armá-lo por
PR após revisar o diff e sua classificação. O GitHub só deverá integrar
quando as regras obrigatórias estiverem satisfeitas. São elegíveis
correções de texto ou documentação interna sem efeito editorial ou de
segurança. Se o diff mudar, reclassifique o PR antes de nova aprovação.
Uma etiqueta pode ajudar a triagem, mas não concede autorização.

Exija aprovação humana explícita e merge manual para workflows, regras do
GitHub, dependências, permissões e RLS, migrações, ingestão e proveniência,
credenciais, infraestrutura, deploy, licença e política editorial. A lista
inclui documentação que muda uma dessas áreas. A política depende de o
mantenedor classificar o PR. Nenhum workflow deste repositório arma
auto-merge.

## Preparação para deploy

Após autorização do ambiente e escolha de hospedagem, use um workflow
separado acionado por push em `main`. Valide e construa no mesmo SHA,
gere um artefato versionado por SHA e entregue exatamente esse artefato
ao job associado ao ambiente protegido de produção. Proponha no ambiente
restrição à `main`, aprovação de publicação, identidade de deploy de
menor privilégio, concorrência de uma publicação por vez e retenção do
artefato anterior para rollback. Valide migrações e recuperação em
ambiente intermediário antes de habilitar a publicação. Esta entrega
prepara o contrato. O único workflow executável é a CI.

## Abertura de PR a partir do Codex

O envio de branches pelo Git está disponível. A chamada GraphQL de
`gh pr create` já retornou `Forbidden`, e a verificação de autenticação
do CLI nesta sessão não confirmou um token válido. Use o formulário do
GitHub em uma sessão do mantenedor com acesso ao repositório. Para
automatizar no futuro, peça ao proprietário que configure uma integração
GitHub autorizada e limitada a este repositório, com o acesso mínimo a PRs
e a conteúdo necessário ao fluxo. Use o mecanismo de autenticação aprovado
da plataforma e teste a criação de um PR de revisão. Preserve as proteções
da branch e o escopo de leitura da CI.

## Validação

Validação local com actionlint, Ruff, `git diff --check`, pip-audit e
PostgreSQL 17. Os testes usam as mesmas migrações e suítes declaradas no
workflow. A execução no GitHub Actions, a seleção do contexto obrigatório,
o auto-merge e o deploy precisam de verificação no GitHub após a revisão.
