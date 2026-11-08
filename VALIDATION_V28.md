# Radar 2.8

## Implementação

- Pré-requisitos Galxe e Zealy. Presença da variável, sintaxe e duplicidade de
  escopos, autorização da coleta e declaração de chave Zealy somente leitura.
  O diagnóstico apresenta campos faltantes e erros 401, 403, 429 e falhas de API.
- Galxe. Queries fixas, detalhes restritos às quests listadas nos Spaces
  autorizados, validação do Space retornado, datas, pontos, tipo de quest e
  menções financeiras na descrição. Menções não comprovam custo obrigatório
  nem ausência de custo. A consulta a regras e recompensas individuais
  documentada depende de endereço e fica fora deste fluxo.
  [Referência](https://docs.galxe.com/galxe-integration/api-reference/quest).
- Zealy. GET oficial, sem redirecionamento, com tipos de recompensas, tarefas
  e condições, datas condicionais e contadores. Configurações e metadados de
  tarefas ficam fora dos relatórios, pois podem conter credenciais.
  A declaração read-only depende da configuração do operador no painel.
  [Endpoint](https://docs.zealy.io/api-reference/quests/list-quests) e
  [autenticação](https://docs.zealy.io/authentication).
- Paginação. Galxe informa páginas adicionais, mas o parâmetro para avançar
  não foi confirmado na referência oficial. Zealy expõe uma lista sem cursor
  documentado para esse GET, com truncamento local sinalizado acima do limite.
- Telegram. Blocos separados por plataforma no relatório normal, com situação,
  catálogo vazio ou contagem de resultados e total de gratuitas confirmadas.
  Catálogos não comprovados ficam no JSON. O dry-run não envia mensagens.
- O status GRATUITA_CONFIRMADA continua reservado à evidência cumulativa de
  disponibilidade, Brasil, custo zero e resgate. Bitcoin Basics mantém a
  classificação inconclusiva da auditoria anterior. BitDegree segue bloqueada.

## Resultado local

318 testes aprovados, com os 310 casos anteriores preservados e oito casos
novos sobre escopos inválidos, declaração somente leitura, extração sanitizada,
cobertura parcial, redirecionamento e validação de Space. Os testes usam mocks.
Ruff, compileall, YAML, actionlint e scanner de credenciais aprovados.

O dry-run local verificou ausência das variáveis e escopos ativos vazios.
Zero consultas reais Galxe e Zealy, zero campanhas novas dessas APIs,
zero recompensas confirmadas gratuitas, brasileiras ou resgatáveis.
A integração real depende da configuração autorizada descrita no README.
