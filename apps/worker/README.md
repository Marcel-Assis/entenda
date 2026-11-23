# Coleta manual de proposições da Câmara

O comando descobre PLs em um intervalo de apresentação e consulta os detalhes
por ID. Use Python 3.12 e um banco PostgreSQL descartável com a
[migração inicial](../../supabase/migrations/20261122131500_camara_ingestion.sql)
já aplicada. O papel dedicado ao worker em um banco compartilhado ainda
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
quarentena e preserva versões anteriores. O modo de reconsulta periódica
de IDs conhecidos e o agendamento ficam para uma entrega posterior.

## Verificação local

Em um banco descartável com a migração aplicada, forneça a conexão pela
variável `ENTENDA_TEST_DATABASE_URL` e execute:

```sh
python -m unittest discover -s apps/worker -v
```

Os testes usam respostas HTTP simuladas e PostgreSQL real.

Verificação manual em 22 de novembro de 2026 com o intervalo acima.
A primeira chamada confirmou uma página e pausou. A retomada confirmou
a segunda página e concluiu a execução. Foram persistidos os IDs oficiais
2416804, 2416826 e 2416830, sem quarentena nesse recorte.
