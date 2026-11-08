# Radar 2.5

Auditoria em 8 de novembro de 2026, horário de Brasília.

## Bitcoin Basics

| Requisito | Evidência ou lacuna |
|---|---|
| Situação em novembro | Curso público e promoção ainda anunciada. Rodada de novembro e sua abertura não confirmadas. |
| Estoque mensal | Não confirmado. O limite anunciado é de 5.000 novos usuários por mês, por ordem de chegada. |
| Brasil | Elegibilidade específica não confirmada. |
| Novo usuário | Confirmado na página oficial do curso. |
| Data de cadastro | Após 01/10/2026 às 00h UTC no anúncio de outubro. Corte de novembro não confirmado. |
| KYC | Exigido nas regras publicadas da promoção. |
| Depósito | Não consta entre as etapas publicadas. Ausência de exigência em novembro não comprovada. |
| Compra | Não consta entre as etapas publicadas. Ausência de exigência em novembro não comprovada. |
| Volume de trading | Não consta entre as etapas publicadas. Ausência de exigência em novembro não comprovada. |
| Staking | Não consta entre as etapas publicadas. Ausência de exigência em novembro não comprovada. |
| Recompensa | Voucher de token de 0,00001 BTC. A Binance documenta crédito na Spot Wallet após resgate válido. Estoque e direito ao voucher atual não verificados. |
| Validade | 14 dias a partir da distribuição segundo o anúncio de outubro. Regra de novembro não confirmada. |
| Taxa de resgate | Não confirmada para a oferta atual. |
| Transferência externa | Taxa e mínimo de saque dependem da rede. A possibilidade de sacar 0,00001 BTC não foi confirmada. |

Classificação **GRATUIDADE_NAO_CONFIRMADA**. A pesquisa pública não incluiu login,
cadastro, KYC, resgate ou transações.

Fontes oficiais. [Curso](https://www.binance.com/en/academy/learn-and-earn/course/bitcoin-basics-BN1106506786176225281),
[anúncio de outubro](https://www.binance.com/de/support/announcement/detail/5fc0f803346b4b5085b0e1c5d16d8b2c),
[FAQ Learn & Earn](https://www.binance.com/en/support/faq/detail/3819c21bd5fb493fa5057c727043cb14),
[resgate de voucher](https://www.binance.com/en/support/faq/detail/8fb78721e97b4138b90b51239f41a9aa)
e [taxas de saque](https://www.binance.com/en/fee/cryptoFee).

## Galxe e Zealy

Galxe usa o POST GraphQL oficial com consultas fixas GetSpaceQuests e GetQuest e
redirecionamentos desativados. O catálogo registra status, datas, participantes,
capacidade, pontos e gas quando disponíveis. Gasless descreve a cobertura do gas
indicado pela API. Gratuidade total, recompensa financeira resgatável, elegibilidade
brasileira, requisitos completos, quizzes e material didático exigem evidência
adicional. O campo documentado de elegibilidade depende de endereço e não é consultado.
A leitura está condicionada a token válido, Spaces autorizados e auditoria vigente.
O limite documentado do plano gratuito é 10 consultas por segundo e 100.000 mensais.
O acesso ao plano e seu custo dependem do Space e do token que o operador já possui.
[Referência](https://docs.galxe.com/galxe-integration/api-reference/quest),
[autenticação](https://docs.galxe.com/galxe-integration/getting-started/authentication)
e [cotas](https://docs.galxe.com/galxe-integration/resources/rate-limits).

Zealy usa GET /public/communities/{subdomain}/quests, que exige chave e papel de
administrador. O servidor valida a autorização e o operador deve usar chave somente
leitura. São até três comunidades, com uma requisição por segundo, tratamento de
429 e remoção do header após a coleta. Quests apagadas, arquivadas ou não publicadas
ficam fora do catálogo. A chave não é necessária para a leitura das observações
públicas do repositório.
[Endpoint](https://docs.zealy.io/api-reference/quests/list-quests),
[autenticação](https://docs.zealy.io/authentication) e [limites](https://docs.zealy.io/rate-limits).

## Resultado da execução

| Indicador | Total |
|---|---|
| Campanhas identificadas | 2, ambas Binance |
| Campanhas ativas pelo calendário oficial | 1, Trading Rewards. Termina em 21/11/2026 às 20h59min59s em Brasília |
| Elegíveis no Brasil confirmadas | 0 |
| Sem depósito ou compra obrigatórios confirmadas para novembro | 0 |
| Com KYC nas regras publicadas | 2, incluindo as regras publicadas de outubro do Bitcoin Basics |
| Recompensas com resgate efetivamente verificado para uma oferta atual | 0 |
| Quizzes | 1 anunciado e 0 perguntas obtidas |
| Consultas reais a Galxe e Zealy | 0 e 0. Dry-run sem credenciais |
| Testes | 298 aprovados, com os 285 casos anteriores incluídos |

Trading Rewards exige pelo menos USD 10.000 de volume elegível para participar da
distribuição. Foi mantida como EXIGE_CAPITAL e fica fora dos alertas de oportunidades.
[Anúncio oficial](https://www.binance.com/en/square/post/383909382526921).

Pytest, Ruff, compileall, parse YAML, actionlint e scanner de credenciais passaram.
Os testes de Galxe e Zealy usam respostas simuladas. O dry-run real usa o cadastro
publicado e confirma o caminho sem credenciais e sem envio ao Telegram. Uma
oportunidade atual, resgatável, elegível no Brasil e com custo inicial zero permanece
sem comprovação.
