# Radar 2.6

Auditoria de 8 de novembro de 2026, horário de Brasília.

## Binance Bitcoin Basics

| Critério | Resultado |
|---|---|
| Abertura da rodada de novembro | Não confirmada na pesquisa oficial em inglês e português. |
| Vagas em novembro | Não confirmadas. O anúncio oficial localizado confirma reposição em outubro e cota anunciada de 5.000 novos usuários mensais. |
| Elegibilidade no Brasil | Não confirmada para a rodada de novembro. O anúncio de outubro alerta para variação por jurisdição. |
| Novo usuário e cadastro | Novo usuário e cadastro após 01/10/2026 00h UTC nas regras de outubro. Corte e regra específicos de novembro não confirmados. |
| KYC | Exigido nas regras publicadas da rodada anterior. Requisito específico de novembro não confirmado. |
| Depósito, compra, trade e staking | Ausência de obrigação não confirmada para novembro. Cada campo permanece desconhecido no cadastro. |
| Valor e formato | 0,00001 BTC em voucher de token conforme oferta publicada. |
| Prazo | 14 dias da distribuição nas regras anteriores. Prazo da rodada de novembro não confirmado. |
| Resgate | A documentação geral descreve crédito na Spot Wallet após resgate de voucher válido. Disponibilidade e direito ao voucher atual não verificados. |
| Saque | Valor mínimo e taxa variam por rede. Não foi possível verificar mínimo e tarifa aplicáveis ao valor do voucher. |

Classificação financeira **GRATUIDADE_NAO_CONFIRMADA**.
[Curso](https://www.binance.com/en/academy/learn-and-earn/course/bitcoin-basics-BN1106506786176225281),
[anúncio oficial de outubro](https://www.binance.com/en/square/post/372547852237367),
[resgate de voucher](https://www.binance.com/en/support/faq/detail/8fb78721e97b4138b90b51239f41a9aa)
e [mínimos e taxas de saque](https://www.binance.com/en-GB/support/faq/crypto-withdrawal-fees-on-binance-d9ff84dccc24423cbe6d59859d86afe3).

## APIs e evidências

- Galxe. Zero consultas reais. Sem token no ambiente e sem Space autorizado no
  cadastro. O conector preserva escopo, limites, pausa após 429 e primeira página
  com indicador de truncamento. A documentação consultada na 2.5 informa
  `hasNextPage`. Não foi verificado parâmetro de continuação para esta consulta,
  portanto a cobertura permanece parcial. A disponibilidade real de recompensa,
  a geografia, as despesas e as exigências de carteira ou assinatura exigem
  evidência específica da quest.
  [Referência GraphQL](https://docs.galxe.com/galxe-integration/api-reference/quest).
- Zealy. Zero consultas reais. Sem chave no ambiente e sem comunidade autorizada
  no cadastro. O GET oficial requer chave com acesso à comunidade administrada.
  O catálogo registra fonte e horário, com custo, prazo e resgate pendentes quando
  o registro não traz evidência suficiente.
  [API oficial](https://docs.zealy.io/api-reference/quests/list-quests).
- A contagem registra respostas HTTP observadas. As respostas simuladas dos testes
  ficam fora do resultado da execução. O dry-run ignorou as duas APIs antes da
  rede. BitDegree segue bloqueada pela auditoria 2.3.

## Resultado

Duas campanhas já cadastradas da Binance. Uma está aberta pelo calendário
publicado e exige volume de negociação. Zero novas campanhas verificadas,
zero oportunidades com gratuidade confirmada, zero elegíveis no Brasil com
confirmação e zero recompensas atuais com resgate comprovado.
[Trading Rewards](https://www.binance.com/en/square/post/383909382526921).

307 testes aprovados, incluindo os 298 anteriores. Os novos casos verificam
resposta vazia, dados ausentes, 429 GraphQL, critérios cumulativos e registro de
HTTP sem headers. A paginação parcial e os erros HTTP continuam cobertos.
Ruff, compileall, YAML, actionlint e scanner de credenciais passaram.
