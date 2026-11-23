# Coleta manual de proposições da Câmara

O comando descobre PLs em um intervalo de apresentação e consulta os detalhes
por ID. Use Python 3.12 e um banco PostgreSQL descartável com a
[migração inicial](../../supabase/migrations/20261122131500_camara_ingestion.sql)
e a [migração de rodízio](../../supabase/migrations/20261122133000_camara_refresh_rotation.sql)
já aplicadas, nessa ordem. O papel dedicado ao worker em um banco compartilhado ainda
precisa ser definido e revisado.

A partir da raiz, em um ambiente virtual Python, instale o driver com
`python -m pip install -r apps/worker/requirements.txt`.
Forneça a conexão do banco local pela variável `ENTENDA_DATABASE_URL`.

```sh
python apps/worker/camara.py --from 2024-01-01 --to 2024-01-31 --items 2 --max-pages 1
python apps/worker/camara.py --resume ID_DA_EXECUCAO --max-pages 1
```

O primeiro JSON contém o ID da execução. O segundo indica o estado e os
totais de páginas confirmadas, versões e quarentenas nesta chamada.
`paused` indica que o orçamento acabou com uma página pendente.
`failed` preserva o cursor e retorna código 1. `completed` indica que
não houve outra página. Um orçamento de uma página não limita a consulta
a um único detalhe. Cada item válido da página pode exigir um GET adicional.

O comando limita retentativas e tamanho de resposta, recusa redirecionamentos
e valida a origem e os filtros do próximo link. A confirmação da página
e o checkpoint são persistidos juntos. Um 404 no detalhe vai para a
quarentena e preserva versões anteriores.

## Reconsulta por ID

Use um lote explícito de até 100 IDs oficiais que já tenham sido coletados.
O comando salva os IDs em ordem crescente, elimina repetições e consulta
cada detalhe sem reaplicar o intervalo de apresentação. Assim uma correção
que mude a data para fora do recorte original ainda pode gerar nova versão.

```sh
python apps/worker/camara.py --refresh 2416804 2416826 --max-items 1
python apps/worker/camara.py --resume ID_DA_RECONSULTA --max-items 1
```

O orçamento padrão é de 20 itens por chamada. O resumo de reconsulta usa
`items` para itens confirmados. Ciclos periódicos podem iniciar um novo lote
com os mesmos IDs. Execute uma chamada por vez. Para selecionar o próximo lote sem informar os IDs, execute:

```sh
python apps/worker/camara.py --refresh-next 20 --max-items 10
```

O comando prioriza IDs sem reconsulta confirmada e depois os confirmados
há mais tempo. Empates são resolvidos pelo ID oficial. Uma chamada retoma
o lote automático pendente mesmo se o tamanho solicitado mudar. Quando
o lote termina, a próxima chamada seleciona outro. Em banco sem propostas,
o comando retorna `empty` sem criar execução ou consultar a API.

Itens em quarentena contam como reconsulta confirmada para o rodízio.
Falhas transitórias esgotadas mantêm o lote no item pendente. Se um item
falhar persistentemente, o lote automático continuará pendente até a
recuperação desse item. A migração inclui registros existentes no rodízio
como IDs sem reconsulta registrada. O agendamento fica para revisão.

## Verificação local

Em um banco descartável com as migrações aplicadas, forneça a conexão pela
variável `ENTENDA_TEST_DATABASE_URL` e execute:

```sh
python -m unittest discover -s apps/worker -v
```

Os testes usam respostas HTTP simuladas e PostgreSQL real.

Verificação manual em 22 de novembro de 2026 com o intervalo acima.
A primeira chamada confirmou uma página e pausou. A retomada confirmou
a segunda página e concluiu a execução. Foram persistidos os IDs oficiais
2416804, 2416826 e 2416830, sem quarentena nesse recorte.

Na mesma validação, a reconsulta dos IDs 2416804 e 2416826 pausou após o
primeiro item e concluiu na retomada, sem gerar versões adicionais.
