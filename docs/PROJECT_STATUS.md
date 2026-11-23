# Estado do projeto Entenda

Atualizado em 23 de novembro de 2026. Este registro está proposto em
`docs/project-tracking`. A referência verificada de `main` é `44a097f`.

Use a coluna **Entrega e verificação** para saber o que existe e como foi
validado. Use **Integração** para saber se a mudança chegou à `main`. Uma
branch publicada ou um PR aberto ainda aguardam integração. Disponibilidade
em produção exige verificação própria e é registrada abaixo.

## Entregas verificadas

| Entrega | Entrega e verificação | Integração e referências |
| --- | --- | --- |
| Fundação documental | Diretrizes, arquitetura, roadmap e política editorial disponíveis e lidos no Git. | Integrada à `main` em `44a097f`. |
| Auditoria das proposições | Listagem, paginação, detalhe e controle 404 verificados na API oficial. | Aguarda merge do [PR #2](https://github.com/Marcel-Assis/entenda/pull/2), da [issue #1](https://github.com/Marcel-Assis/entenda/issues/1). Branch `docs/audit-camara-proposicoes`, commit `b2252a7`. |
| Auditoria dos filtros temporais | 14 consultas reais compararam ano, apresentação, tramitação e histórico. | Aguarda revisão e merge. Referência à [issue #3](https://github.com/Marcel-Assis/entenda/issues/3). Branch `docs/audit-camara-filtros-temporais`, commit `62b751f`. [PR #4](https://github.com/Marcel-Assis/entenda/pull/4) |
| Modelo de ingestão | Proposta documental de evidência, versões e checkpoint, verificada no Git. | Aguarda revisão e merge. Branch `docs/camara-ingestion-model`, commit `a44f7c7`. [PR #5](https://github.com/Marcel-Assis/entenda/pull/5) |
| Migração PostgreSQL | Código implementado e testado em PostgreSQL 17.12 vazio, com integridade referencial, rollback e RLS. | Aguarda revisão e merge. Branch `feat/camara-ingestion-schema`, commit `cd2e083`, inclui o modelo documental. [PR #6](https://github.com/Marcel-Assis/entenda/pull/6) |
| Coletor manual | Código implementado e verificado com quatro testes de integração, suíte SQL e coleta real de três PLs com pausa e retomada. | Aguarda revisão e merge. Branch `feat/camara-discovery`, commit `d73d3bd`. [PR #7](https://github.com/Marcel-Assis/entenda/pull/7) |
| Reconsulta por ID | Código implementado e verificado com cinco testes de integração, suíte SQL e reconsulta real de dois IDs. | Aguarda revisão e merge. Branch `feat/camara-refresh`, commit `104069c`. [PR #8](https://github.com/Marcel-Assis/entenda/pull/8) |
| Seleção automática de lotes | Código implementado e verificado com seis testes de integração, suíte SQL e rodízio real de três IDs. | Aguarda revisão e merge. Branch `feat/camara-refresh-batches`, commit `0f31c8e`. [PR #9](https://github.com/Marcel-Assis/entenda/pull/9) |
| CI do worker e PostgreSQL | Workflow implementado. actionlint, Ruff, pip-audit, suíte SQL e seis testes Python verificados localmente. A execução no GitHub permanece pendente. | Branch `ci/worker-postgres`, commit `620e41d`. A abertura de PR segue bloqueada nesta sessão. [Comparação](https://github.com/Marcel-Assis/entenda/compare/feat/camara-refresh-batches...ci/worker-postgres?expand=1) |
| Base web em Next.js e TypeScript | Instalação congelada, typecheck, build, HTTP 200/404 e auditoria de produção verificados localmente. | Branch `feat/web-foundation`, commit `0ae14da`. Aguarda abertura do PR. [Comparação](https://github.com/Marcel-Assis/entenda/compare/main...feat/web-foundation?expand=1) |

## Em andamento e próximas etapas

| Estado | Atividade | Próxima ação |
| --- | --- | --- |
| Em andamento | Instituir acompanhamento persistente. | Revisar o [PR #10](https://github.com/Marcel-Assis/entenda/pull/10) e os vínculos deste registro. |
| Pendente | Revisar e integrar as entregas da Câmara em ordem de dependência. | Revisar as auditorias, o modelo e a migração antes das branches do worker. |
| Pendente | Validar a CI no GitHub. | Abrir o PR de CI, verificar a execução hospedada e revisar a proteção da main. |
| Bloqueada | Formalizar a licença open-source. | Obter decisão do mantenedor. |
| Bloqueada | Ativar o worker em banco compartilhado ou com agendamento. | Revisar permissões, operação e ambiente antes da ativação. |

## Produção

Nenhum deploy nem funcionalidade em produção foi verificado nesta execução.
Os testes na API oficial usaram banco descartável.

As causas, impactos e ações para as pendências externas constam em
[Bloqueios](BLOCKERS.md).
