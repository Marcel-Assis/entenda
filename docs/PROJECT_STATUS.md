# Estado do projeto Entenda

Atualizado em 22 de novembro de 2026. Este registro está proposto em
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
| Auditoria dos filtros temporais | 14 consultas reais compararam ano, apresentação, tramitação e histórico. | Aguarda abertura de PR da [issue #3](https://github.com/Marcel-Assis/entenda/issues/3). Branch `docs/audit-camara-filtros-temporais`, commit `62b751f`. [Comparação](https://github.com/Marcel-Assis/entenda/compare/main...docs/audit-camara-filtros-temporais?expand=1) |
| Modelo de ingestão | Proposta documental de evidência, versões e checkpoint, verificada no Git. | Aguarda abertura de PR. Branch `docs/camara-ingestion-model`, commit `a44f7c7`. [Comparação](https://github.com/Marcel-Assis/entenda/compare/main...docs/camara-ingestion-model?expand=1) |
| Migração PostgreSQL | Código implementado e testado em PostgreSQL 17.12 vazio, com integridade referencial, rollback e RLS. | Aguarda abertura de PR. Branch `feat/camara-ingestion-schema`, commit `cd2e083`, inclui o modelo documental. [Comparação](https://github.com/Marcel-Assis/entenda/compare/main...feat/camara-ingestion-schema?expand=1) |
| Coletor manual | Código implementado e verificado com quatro testes de integração, suíte SQL e coleta real de três PLs com pausa e retomada. | Aguarda abertura de PR sobre a migração. Branch `feat/camara-discovery`, commit `d73d3bd`. [Comparação](https://github.com/Marcel-Assis/entenda/compare/feat/camara-ingestion-schema...feat/camara-discovery?expand=1) |
| Reconsulta por ID | Código implementado e verificado com cinco testes de integração, suíte SQL e reconsulta real de dois IDs. | Aguarda abertura de PR sobre o coletor. Branch `feat/camara-refresh`, commit `104069c`. [Comparação](https://github.com/Marcel-Assis/entenda/compare/feat/camara-discovery...feat/camara-refresh?expand=1) |
| Seleção automática de lotes | Código implementado e verificado com seis testes de integração, suíte SQL e rodízio real de três IDs. | Aguarda abertura de PR sobre a reconsulta. Branch `feat/camara-refresh-batches`, commit `0f31c8e`. [Comparação](https://github.com/Marcel-Assis/entenda/compare/feat/camara-refresh...feat/camara-refresh-batches?expand=1) |

## Em andamento e próximas etapas

| Estado | Atividade | Próxima ação |
| --- | --- | --- |
| Em andamento | Instituir acompanhamento persistente. | Revisar a branch `docs/project-tracking` e os vínculos deste registro. |
| Pendente | Revisar e integrar as entregas da Câmara em ordem de dependência. | Revisar as auditorias, o modelo e a migração antes das branches do worker. |
| Pendente | Automatizar verificações do worker e preparar a base web da Fase 1. | Priorizar CI local ao repositório com PostgreSQL descartável. |
| Bloqueada | Formalizar a licença open-source. | Obter decisão do mantenedor. |
| Bloqueada | Ativar o worker em banco compartilhado ou com agendamento. | Revisar permissões, operação e ambiente antes da ativação. |

## Produção

Nenhum deploy nem funcionalidade em produção foi verificado nesta execução.
Os testes na API oficial usaram banco descartável.

As causas, impactos e ações para as pendências externas constam em
[Bloqueios](BLOCKERS.md).
