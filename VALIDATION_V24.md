# Radar 2.4 — auditoria multiplataformas e implementação

Base: 08b28eeba40902ec762cd854d6ff80d7b77fc07e. Auditoria em 08/11/2026.

## Pesquisa real em fontes oficiais

| Plataforma | Situação para este radar | Evidência e limite |
|---|---|---|
| Binance Academy | AUTORIZACAO_NECESSARIA | https://www.binance.com/en/terms não expôs conteúdo integral; termos regionais https://www.binance.com/en-JP/about-legal/terms restringem crawlers. Não foi identificada API documentada L&E. |
| CoinMarketCap | AUTORIZACAO_NECESSARIA | https://coinmarketcap.com/terms/ seção 6 restringe screen scrape/reutilização sem permissão. API de mercado não comprova acesso a Earn. |
| Galxe | API_OFICIAL, escopo restrito | https://docs.galxe.com/galxe-integration/getting-started/quick-start exige token. https://help.galxe.com/en/articles/8506982-getting-started-with-galxe-quest descreve depósito para criar Space, não custo universal para participantes. Nenhum depósito foi realizado. Termos gerais tentados não acessíveis; não se presume licença para scraping. |
| Layer3 | AUTOMACAO_PROIBIDA | https://app.layer3.xyz/terms seção 7 item 19. Página principal existe, mas a aplicação retornou 403 na consulta de pesquisa. |
| Zealy | API_OFICIAL, comunidade administrada | https://docs.zealy.io/api-reference/quests/list-quests exige admin; https://docs.zealy.io/authentication exige chave. Plano gratuito inclui integrações em https://zealy.io/docs/start-guide/billing-and-plans; limite documentado 50 RPS, implementação usa no máximo uma consulta por segundo. |
| Intract | AUTOMACAO_PROIBIDA | https://intract.gitbook.io/website-policies/intract-terms-of-use proíbe robôs e extração. Homepage atual não acessível na pesquisa; não se confirma campanha ativa. |
| QuestN | AUTORIZACAO_NECESSARIA | https://questn.com/ e www retornaram 502 na pesquisa. Termos e API não verificados; não inventar endpoint nem declarar encerramento. |
| Revolut | ACESSO_PUBLICO_MANUAL | https://www.revolut.com/en-BR/legal/website-terms-and-conditions/ permite extratos pessoais, sem autorização expressa de crawler. FAQ Brasil confirma educação; recompensa e curso variam por conta/região. |
| BitDegree | AUTOMACAO_PROIBIDA | Barreira 2.3 mantida e agora aplicada também ao HTTP legado. Nenhuma nova tentativa. |

O link de termos Zealy, obtido do rodapé oficial, retornou 400 no provedor de pesquisa.
A autorização usada limita-se ao GET documentado de uma comunidade administrada, não
à navegação automatizada do site. Galxe não foi implementada porque acesso/escopo/custo
não foram validados para esta conta. Não há fonte classificada AUTOMACAO_PERMITIDA
para scraping geral. HTTP da pesquisa acima não é inventado como HTTP de execução do
bot: quando não houve requisição do coletor, o campo do relatório permanece null.

## Campanhas efetivamente encontradas

1. Bitcoin Basics, Binance: https://www.binance.com/en/academy/learn-and-earn/course/bitcoin-basics-BN1106506786176225281
   anuncia 0.00001 BTC, novos usuários, 5.000 por mês. FAQ
   https://www.binance.com/en/support/faq/detail/3819c21bd5fb493fa5057c727043cb14
   confirma segmentação e KYC. Não comprovados Brasil, saldo da cota de novembro e
   todas as obrigações financeiras. Portanto gratuidade e disponibilidade não confirmadas.
2. Campanha de negociação da conta oficial Binance:
   https://www.binance.com/en/square/post/383909382526921
   anúncio exige US$ 10.000 de volume qualificado para compartilhar pool de 20 milhões
   USDC; encerra 22/11/2026 07:59:59 UTC+8 (21/11/2026 23:59:59 UTC). Exige capital.

CoinMarketCap apresentou exemplos históricos, não campanhas atuais comprovadas.
Zealy mostrou zero itens no bloco público de recompensas garantidas consultado; isso
não prova inexistência de campanhas na plataforma. Revolut confirma Crypto Learn no
Brasil, mas o link de recompensas do FAQ retornou 404; isso não prova extinção do programa.
Layer3 menciona CUBEs e onchain tasks; não há campanha individual gratuita comprovada.
Nenhuma questão concreta de quiz foi obtida por acesso automatizado autorizado.
As observações acima vieram de pesquisa manual, não do conector API nem de testes.

## Mudanças

Novos: config/platforms.json, config/campaign_observations.json,
src/platform_permissions.py, src/multiplatform.py, tests/test_multiplatform.py,
este documento e docs/platform-audit-v24.json (relatório real dry-run).
Alterados: config/sources.json, src/utils.py, src/state.py, workflow e README.
Nenhuma dependência, serviço pago ou endpoint privado adicionado.
Os módulos antigos são preservados, mas caminhos de coleta sem permissão ficam
bloqueados: explicitamente BitDegree, Binance L&E e Revolut no cadastro legado.

## Verificação

285 testes passaram: os 252 existentes intactos e 33 novos. Todos offline com rede
bloqueada. Cenários novos cobrem obrigações financeiras, KYC, taxas, pontos, evidência
oficial, geografia, expiração, fontes desativadas, guardas de URL, API GET documentada,
chave ausente, limpeza de header, falhas, cache, atualização, encerramento, dry-run,
revisão vencida, análise de quiz com permissão explícita e redação de credencial.
Executados pytest, Ruff, compileall, YAML, actionlint e scanner de credenciais.

Executado python -m src.multiplatform --dry-run com configuração real: nove fontes
auditadas; zero registros API (sem chave e comunidades administradas); duas observações
manuais; zero gratuitas verificadas; zero perguntas; zero Telegram; estado não alterado.
Nenhuma chamada API real foi realizada sem credenciais legítimas; conector validado com
mocks, não declarado operacional com uma conta real. Nenhuma mensagem simulada enviada.
Relatório preservado em docs/platform-audit-v24.json. Não confundir 0 chamadas autorizadas
com verificação em tempo real de ausência de campanhas.

## Limite frente ao objetivo

A infraestrutura, classificação e controle de permissões foram implementados, mas o
critério de encontrar uma oportunidade atual, financeira e zero investimento para um
brasileiro ainda não foi atingido. Não se promete busca diária ampla sem acessos
permitidos. APIs de projetos/admin não são uma licença de coleta global; campanha
oficial existente não comprova elegibilidade individual nem prêmio disponível.
