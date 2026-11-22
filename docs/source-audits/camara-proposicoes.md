# Auditoria técnica — proposições da Câmara dos Deputados

Issue [#1](https://github.com/Marcel-Assis/entenda/issues/1). Consulta realizada em **22 de novembro de 2026**, com horários em UTC e requisições GET sem credenciais. O acesso HTTPS pela nuvem funcionou nesta sessão. O erro de túnel 403 registrado anteriormente não se repetiu.

## Documentação oficial

O [portal](https://dadosabertos.camara.leg.br/) e a [interface Swagger](https://dadosabertos.camara.leg.br/swagger/api.html) responderam HTTP 200. A [especificação](https://dadosabertos.camara.leg.br/api/v2/api-docs), consultada às 13:11:59 UTC, identifica a edição do serviço como 0.4.361 e documenta:

- `GET /api/v2/proposicoes` para a listagem. Entre os parâmetros estão `id`, `siglaTipo`, `numero`, `ano`, `pagina`, `itens`, `ordem` e `ordenarPor`. A paginação começa em 1, com 15 itens por padrão e limite documentado de 100 itens por requisição. `id` é uma opção de ordenação.
- `GET /api/v2/proposicoes/{id}` para o detalhe por identificador numérico. A documentação lista respostas 200, 400 e 404 para ambas as operações.
- JSON e XML são formatos documentados. A auditoria usou apenas JSON. `dataInicio` e `dataFim` são descritos como filtros de tramitação. `dataApresentacaoInicio` e `dataApresentacaoFim` são descritos como filtros de apresentação. Esses filtros de data ficaram fora da amostra.

## Recorte e evidência

Projetos de lei com `siglaTipo=PL` e `ano=2024`, em ordem crescente de `id`. O ano fixo evita depender do ano corrente. O limite da amostra foi de duas páginas com dois itens cada, um detalhe consultado duas vezes e um controle negativo. Para reproduzir, faça um GET com `Accept: application/json` nas URLs abaixo. Para a segunda página, prefira o `href` de `links` cujo `rel` seja `next` na resposta corrente.

| Início em UTC | Consulta | HTTP | Resultado |
| --- | --- | --- | --- |
| 13:11:44 | [Listagem, página 1](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ano=2024&ordem=ASC&ordenarPor=id&itens=2&pagina=1) | 200 | IDs 253500 e 380852 |
| 13:12:00 | [Página 2, via next](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ano=2024&ordem=ASC&ordenarPor=id&pagina=2&itens=2) | 200 | IDs 510035 e 582036 |
| 13:12:06 e 13:12:15 | [Detalhe 253500](https://dadosabertos.camara.leg.br/api/v2/proposicoes/253500) | 200 nas duas consultas | Mesmo ID e mesmo SHA-256 dos corpos brutos |
| 13:12:06 | [Detalhe 0](https://dadosabertos.camara.leg.br/api/v2/proposicoes/0) | 404 | JSON com `status`, `title`, `detail`, `instance` e `code`; código 6 |

### Paginação e campos observados

- Na listagem, `dados` é um array e `links` contém objetos com `rel` e `href`. As duas páginas apresentaram `self`, `first`, `last` e `next`; a segunda também apresentou `previous`. O `next` da segunda apontou para a página 3. O `last` indicou página 2221 nas duas respostas. A última página ficou fora da amostra. Os quatro IDs estavam em ordem crescente, sem repetição entre as duas páginas; isso não estabelece estabilidade durante uma varredura mais longa.
- Os quatro itens continham `id`, `uri`, `siglaTipo`, `codTipo`, `numero`, `ano`, `ementa` e `dataApresentacao`. Todos tinham `ano=2024`, mas as datas de apresentação vieram como `2004-05-13T14:41`, `2007-12-12T16:23`, `2011-06-22T12:12` e `2013-06-25T17:54`, na ordem dos IDs acima. Isso diverge da descrição de `ano` no Swagger como ano de apresentação. Preserve ambos os campos e valide os filtros de data antes de usá-los para restringir cobertura.
- No detalhe, `dados` é um objeto e o único link era `self`. O ID, o número 2597 e o ano 2024 corresponderam à listagem. O detalhe acrescentou campos como `statusProposicao`, `descricaoTipo`, `keywords`, `uriAutores` e `urlInteiroTeor`. Em `statusProposicao`, foram observados `dataHora`, `sequencia`, `descricaoSituacao` e `codSituacao`, entre outros. `dataHora` veio como `2024-12-17T00:00`, sem deslocamento explícito de fuso. `uriPropPrincipal`, `uriPropAnterior`, `uriPropPosterior`, `urnFinal`, `texto` e `justificativa` vieram como `null`. O normalizador deve distinguir campo ausente, valor nulo e string vazia.
- As duas respostas de detalhe tiveram SHA-256 `d1bf086b7380a149016181ad6807c0325c4352dad5018cc33212f976563ba4c8`. A igualdade registra apenas a repetição imediata. Ela não demonstra periodicidade, atraso de publicação ou estabilidade histórica.

### Limitações

A amostra não estabeleceu cobertura histórica, fuso dos horários sem deslocamento, regularidade das atualizações, termos de reutilização ou limite de requisições por tempo. O limite documentado por página não equivale a uma cota de tráfego. Respostas reais vazias, 429, 5xx e timeout não foram observadas. Não houve teste de carga. A amostra também não estabelece que `statusProposicao.dataHora` mude sempre que o conteúdo do detalhe for corrigido.

## Estratégia proposta

Identificar cada registro por fonte e `id` oficial. Preservar corpo bruto com URL consultada, horário UTC da coleta e SHA-256. Manter versão normalizada vinculada à evidência bruta e comparar campos normalizados para distinguir alterações de conteúdo de mudanças de serialização.

Em cada execução, fixar filtros, ordem e orçamento de páginas. Validar origem HTTPS e caminho do próximo link antes de segui-lo. Persistir a página, o tratamento dos itens e o checkpoint na mesma transação. Detectar ciclos de paginação e deduplicar por ID entre páginas e reexecuções. Após interrupção longa, permitir reiniciar o recorte com deduplicação, pois o índice da página pode ter mudado.

Para atualizar, reconsultar detalhes de IDs conhecidos em lotes limitados. Avaliar uma janela de tramitação com sobreposição como forma de descobrir candidatos, após validar sua semântica com dados reais. Uma reconsulta periódica do recorte é necessária para detectar correções que não apareçam nessa janela. Registrar 404 ou ausência para investigação antes de qualquer decisão de remoção. Limitar retentativas de falhas transitórias, com backoff e respeito a `Retry-After` quando fornecido.

## Critérios de aceitação do primeiro coletor

- [ ] Executar manualmente um recorte com tipo, filtros, ordem e orçamento explícitos. Seguir `next` sob a origem oficial, chamar detalhes por ID e registrar o motivo de término.
- [ ] Persistir evidência bruta, URL, horário, hash e ID oficial. Verificar correspondência entre o ID solicitado e o retornado e encaminhar dados inválidos ou ambíguos para quarentena com diagnóstico.
- [ ] Reexecutar a mesma entrada sem duplicar registros ou versões de conteúdo. Uma alteração válida no detalhe gera nova versão vinculada ao bruto e preserva o histórico.
- [ ] Simular falha antes da confirmação de uma página e provar que a retomada não pula itens nem duplica versões. Detectar paginação repetida e link fora da origem.
- [ ] Testar com amostras locais lista vazia, múltiplas páginas, IDs repetidos, campos ausentes ou nulos, JSON inválido, ID divergente, 404, 429, 5xx e timeout. Verificar retentativas limitadas e que ausência ou falha não apague histórico.
- [ ] Produzir logs ou resumo com páginas lidas, itens novos, alterados e em quarentena, e distinguir execução incompleta de execução concluída sem novidades.
- [ ] Fazer uma validação real de baixo volume no recorte aprovado e conferir IDs, valores e proveniência contra a fonte oficial.
