# Modelo de ingestão de proposições da Câmara

Proposta para a Fase 1. O primeiro worker Python será executado manualmente e persistirá dados em PostgreSQL. O recorte de validação usa PLs com intervalo explícito de apresentação, ordenação por ID e orçamento de páginas. A trilha de auditoria cobre a [listagem e o detalhe](https://github.com/Marcel-Assis/entenda/pull/2) e os [filtros temporais](https://github.com/Marcel-Assis/entenda/blob/docs/audit-camara-filtros-temporais/docs/source-audits/camara-filtros-temporais.md).

## Registros e chaves

| Registro | Chave e conteúdo |
| --- | --- |
| Corpo bruto | SHA-256 dos bytes recebidos após decodificação do transporte. Guardar os bytes sem reserializar o JSON. Reutilizar o corpo armazenado quando o hash coincidir. |
| Resposta observada | ID próprio, execução, URL consultada, horário UTC da coleta, status HTTP e referência ao corpo, quando houver. Duas coletas do mesmo corpo produzem observações distintas. Uma falha sem resposta HTTP tem diagnóstico de transporte e status ausente. |
| Proposição | Chave única `(fonte, id_oficial)`. Guardar o ID numérico fornecido pela Câmara e uma referência à versão corrente. Número, ano e sigla fazem parte da representação da fonte. |
| Versão da proposição | Chave `(fonte, id_oficial, sequencia)`, referência à resposta de detalhe e hash do conteúdo normalizado com a versão do normalizador. Guardar os campos normalizados e evidência de origem. Comparar com a versão corrente, de modo que a sequência A → B → A produza três versões. |
| Execução e checkpoint | ID próprio, modo, escopo imutável da consulta, estado, cursor pendente, páginas confirmadas e horários. No modo de descoberta, o cursor é a URL da próxima página. No modo de reconsulta, é a posição no lote fixo de IDs da execução. |
| Quarentena | Execução, referência à resposta e posição do item quando aplicável, ID se legível e código do motivo. Usar a evidência bruta para diagnóstico e eventual reprocessamento. |

A representação normalizada inicial preserva `siglaTipo`, `codTipo`, `numero`, `ano`, `ementa` e `dataApresentacao`, além do estado informado no detalhe quando disponível. Conservar datas da fonte sem inventar fuso e distinguir ausência, nulo e vazio onde o contrato exigir. Calcular o hash sobre JSON determinístico, com chaves ordenadas, lista de campos explícita e sem metadados de coleta. A identidade oficial deve coincidir entre item listado e detalhe. Registro de listagem é evidência de descoberta e o detalhe fundamenta a versão. A resposta observada preserva a URL mesmo quando o corpo já existe.

## Confirmação e retomada

1. Ler a página e buscar os detalhes com timeout e retentativas limitadas, fora de transação. Validar origem HTTPS, caminho e escopo do link seguinte; detectar ciclos comparando parâmetros normalizados das páginas confirmadas. Usar a sequência de IDs como diagnóstico quando uma URL diferente repetir uma página.
2. Confirmar página, corpos e observações, novas versões, quarentenas e avanço do cursor em uma única transação. Serializar confirmações concorrentes para a mesma execução pela linha de checkpoint e conferir se o cursor ainda é o esperado. Atualizar cada proposição sob bloqueio da sua linha para evitar versões duplicadas. O primeiro worker roda uma execução por vez.
3. Se a página falhar após esgotar as retentativas, registrar a falha e manter o cursor. Uma resposta inválida que impeça interpretar a página inteira também impede o avanço. Um item isolado e inválido pode ir para quarentena. Tratar 404 no detalhe como ausência observada para investigação, preservando qualquer versão anterior.
4. Distinguir execução concluída sem novidades, execução interrompida pelo orçamento com cursor disponível e falha retomável. Se o processo cair após a confirmação, retoma do cursor persistido. Se cair antes, relê a página. Como a paginação pode mudar, uma retomada após pausa longa pode ser substituída por uma nova varredura do mesmo recorte com deduplicação.

## Política de atualização e verificações

- Descobrir IDs por janela de apresentação e confirmar a data no retorno. Preservar `ano` separadamente. Reconsultar detalhes de IDs conhecidos em lotes. Uma janela de tramitação pode sugerir candidatos, mas a presença do ID na listagem por si só não comprova evento.
- Validar a primeira migração em banco vazio e provar que rejeita chaves oficiais duplicadas e referências de versão ou evidência inválidas. Testar observações distintas para corpo idêntico, nova versão para alteração e histórico A → B → A.
- Simular falha antes e depois da confirmação, checkpoint concorrente, link circular ou fora da origem, divergência de ID, página vazia, 404, 429, 5xx, timeout e JSON inválido. Verificar que falhas e registros ausentes preservam histórico e que os logs distinguem falha de coleta de ausência de novidades.
- Manter o armazenamento bruto no lado do servidor, limitar acesso na migração antes de expor a API e verificar as políticas com os papéis previstos. A publicação editorial segue o fluxo de revisão humana do projeto.

A primeira entrega executável proposta é a migração com restrições de integridade e testes locais de persistência. O worker fica para uma entrega seguinte, com os contratos de confirmação e retomada acima.
