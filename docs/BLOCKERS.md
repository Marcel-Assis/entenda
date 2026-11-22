# Bloqueios do projeto Entenda

Atualizado em 22 de novembro de 2026. Este registro está proposto em
`docs/project-tracking`. Para cada bloqueio, registre a condição observada,
o impacto e a ação necessária. Quando houver evidência de resolução,
registre-a junto ao item ou mova-o para o histórico abaixo.

## Abertos

| Bloqueio | Causa observada | Impacto | Ação necessária |
| --- | --- | --- | --- |
| Abertura de PR pela automação | `gh pr create` recebeu `Forbidden` em `https://api.github.com/graphql`. O push via Git funcionou. | As branches publicadas sem PR precisam de revisão pelo GitHub. O erro também impede usar essa via para publicar um resumo externo. | Usar uma sessão com permissão para abrir PRs e publicar o resumo, ou abrir pelos links de comparação em [Estado do projeto](PROJECT_STATUS.md). Os PRs #2 e #4–#10 já foram abertos pelo mantenedor. |
| Licença open-source | A licença ainda não foi formalizada em `LICENSE`. | A concessão de licença de código segue pendente. | O mantenedor deve confirmar a licença e a titularidade aplicável antes de publicar os termos. [Guia de contribuição](CONTRIBUTING.md) |
| Worker em banco compartilhado | O papel dedicado do worker, suas permissões e as políticas correspondentes aguardam revisão. | Os testes locais passaram. A execução compartilhada depende dessa revisão. | Aprovar o escopo de acesso, configurar o papel e verificar permissões com credenciais de teste antes de ativar. |
| Agendamento de reconsulta | A seleção de lotes está implementada, e a operação recorrente ainda precisa de janela, limites e responsável por falhas. | O rodízio pode ser acionado manualmente. Um erro persistente mantém o lote automático pendente. | Definir operação e alertas, confirmar o acesso compartilhado e aprovar a ativação. [Branch do rodízio](https://github.com/Marcel-Assis/entenda/tree/feat/camara-refresh-batches) |

| Políticas de CI e publicação | A execução hospedada e a proteção da main ainda aguardam revisão. | A CI foi validada localmente. Checks obrigatórios, auto-merge e deploy ainda não estão habilitados nesta entrega. | Abrir o [PR de CI](https://github.com/Marcel-Assis/entenda/compare/feat/camara-refresh-batches...ci/worker-postgres?expand=1), verificar o check no GitHub e aprovar as regras antes de aplicá-las. |

## Resolvidos

- **Acesso à API da Câmara na nuvem.** O proxy bloqueava o túnel HTTPS com
  403. As auditorias e as coletas reais posteriores confirmaram acesso à API
  oficial. [Issue #1](https://github.com/Marcel-Assis/entenda/issues/1) ·
  [Issue #3](https://github.com/Marcel-Assis/entenda/issues/3)
