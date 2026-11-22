# Auditoria dos filtros temporais de proposições da Câmara

Complementa a [auditoria inicial (issue #1 e PR #2)](https://github.com/Marcel-Assis/entenda/pull/2) e responde à [issue #3](https://github.com/Marcel-Assis/entenda/issues/3). As requisições foram feitas em 22 de novembro de 2026. Os horários abaixo são UTC.

## Contrato documentado

O [OpenAPI oficial](https://dadosabertos.camara.leg.br/api/v2/api-docs) respondeu HTTP 200 às 13:15:34. Ele descreve `ano` como um ou mais anos de apresentação no formato `AAAA`, `dataApresentacaoInicio` e `dataApresentacaoFim` como os extremos de um intervalo de apresentação, e `dataInicio` e `dataFim` como os extremos de um intervalo em que houve tramitação. Os testes enviaram ambos os extremos de cada janela. Valores padrão, regras gerais de inclusão dos extremos e fuso dos valores retornados não foram validados.

## Consultas reproduzíveis

Use GET com `Accept: application/json`. As consultas A–I foram limitadas à primeira página com dois projetos de lei, ordenados por ID crescente. A janela de janeiro de 2024 permite comparar os filtros em um período fixo. O ID 253500 veio da auditoria inicial e serve de controle por ter ano e data de apresentação divergentes.

| UTC | Consulta | HTTP | IDs em ordem |
| --- | --- | --- | --- |
| 13:15:24 | [A · ano 2024](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&ano=2024) | 200 | 253500, 380852 |
| 13:15:24 | [B · apresentação em janeiro](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&dataApresentacaoInicio=2024-01-01&dataApresentacaoFim=2024-01-31) | 200 | 2416804, 2416826 |
| 13:15:24 | [C · tramitação em janeiro](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&dataInicio=2024-01-01&dataFim=2024-01-31) | 200 | 356412, 409035 |
| 13:15:25 | [D · ano e apresentação](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&ano=2024&dataApresentacaoInicio=2024-01-01&dataApresentacaoFim=2024-01-31) | 200 | 2416804, 2416826 |
| 13:15:27 | [E · ano e tramitação](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&ano=2024&dataInicio=2024-01-01&dataFim=2024-01-31) | 200 | 253500, 380852 |
| 13:15:28 | [F · controle e apresentação em janeiro](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&id=253500&dataApresentacaoInicio=2024-01-01&dataApresentacaoFim=2024-01-31) | 200 | `dados: []`, só link `self` |
| 13:15:31 | [G · controle no dia da apresentação](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&id=253500&dataApresentacaoInicio=2004-05-13&dataApresentacaoFim=2004-05-13) | 200 | 253500 |
| 13:15:32 | [H · controle e tramitação em 17/12/2024](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&id=253500&dataInicio=2024-12-17&dataFim=2024-12-17) | 200 | 253500 |
| 13:15:33 | [I · controle e tramitação em 01/01/2024](https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ordem=ASC&ordenarPor=id&itens=2&pagina=1&id=253500&dataInicio=2024-01-01&dataFim=2024-01-01) | 200 | 253500 |
| 13:15:34 | [J · detalhe do controle](https://dadosabertos.camara.leg.br/api/v2/proposicoes/253500) | 200 | 253500 |
| 13:15:43 | [Histórico de 253500 em janeiro](https://dadosabertos.camara.leg.br/api/v2/proposicoes/253500/tramitacoes?dataInicio=2024-01-01&dataFim=2024-01-31) | 200 | `dados: []` |
| 13:15:44 | [Histórico de 356412 em janeiro](https://dadosabertos.camara.leg.br/api/v2/proposicoes/356412/tramitacoes?dataInicio=2024-01-01&dataFim=2024-01-31) | 200 | Evento em `2024-01-30T00:00` |
| 13:15:45 | [Histórico de 409035 em janeiro](https://dadosabertos.camara.leg.br/api/v2/proposicoes/409035/tramitacoes?dataInicio=2024-01-01&dataFim=2024-01-31) | 200 | Evento em `2024-01-18T00:00` |

| ID | Número | Ano | `dataApresentacao` |
| --- | --- | --- | --- |
| 253500 | 2597 | 2024 | `2004-05-13T14:41` |
| 380852 | 411 | 2024 | `2007-12-12T16:23` |
| 2416804 | 2 | 2024 | `2024-01-03T15:27` |
| 2416826 | 3 | 2024 | `2024-01-10T18:15` |
| 356412 | 1375 | 2007 | `2007-06-20T15:44` |
| 409035 | 4022 | 2008 | `2008-09-03T18:20` |

## Achados e limites

- O detalhe de 253500 confirmou número, ano e data de apresentação da listagem. Seu `statusProposicao.dataHora` era `2024-12-17T00:00`. A resposta ao filtro `ano=2024` incluiu datas de apresentação anteriores a 2024, em divergência com a descrição do OpenAPI.
- A primeira página com filtro de apresentação incluiu datas dentro de janeiro, com e sem `ano=2024`. O controle ficou de fora de janeiro de 2024 e apareceu na janela de um dia em 2004. A igualdade de B e D vale apenas para a primeira página observada.
- A listagem por tramitação encontrou dois IDs antigos com eventos no histórico de janeiro. Com `ano=2024` combinado, incluiu 253500, cujo histórico para janeiro estava vazio. A listagem pelo ID também o incluiu em 1º de janeiro. Isso demonstra uma divergência entre os resultados dos endpoints para o controle. A causa, a precedência dos filtros e a cobertura de cada endpoint permanecem indeterminadas. Um histórico vazio, por si só, não comprova ausência de tramitação.
- A amostra não estabelece cobertura histórica, completude, validade de combinações para todas as páginas ou atraso com que correções entram na fonte.

## Decisão para o primeiro coletor

1. **Recorte e descoberta.** Usar o par de filtros de apresentação para um recorte inicial explícito de PLs. Verificar `dataApresentacao` no retorno e registrar valores fora da janela ou ausentes. Preservar também `ano` e número. Redescobrir IDs com janelas sobrepostas para reduzir lacunas por registros inseridos tardiamente.
2. **Reconsulta.** Reconsultar IDs conhecidos pelo endpoint de detalhe em lotes limitados. A janela de tramitação pode gerar candidatos adicionais, desde que haja conferência do histórico quando for necessário afirmar a existência de um evento. Manter reconsulta periódica dos detalhes independentemente da janela para encontrar correções retroativas.
3. **Testes antes de ampliar cobertura.** Exercitar janela com resultados e vazia, limites de dia, paginação sob filtros combinados e divergência entre listagem e histórico. Preservar o caso 253500 como teste com amostra local para assegurar que `ano` não seja convertido em data de apresentação e que uma inclusão na listagem não gere automaticamente um evento. Depois de implementar, comparar um lote real com o detalhe oficial e validar idempotência e retomada.
