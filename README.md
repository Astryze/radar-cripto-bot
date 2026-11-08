# Radar Cripto 2.0

Radar de campanhas públicas Web3 com participação sem investimento inicial. Python
3.12, GitHub Actions, fontes oficiais e Telegram, sem servidor ou API paga.

## Executar

1. Em **Settings → Secrets and variables → Actions**, mantenha os Secrets
   `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`. Nunca coloque seus valores no código.
2. Abra o bot no Telegram e envie `/start`. O ID deve pertencer à conta que iniciou
   a conversa; em grupos, o bot precisa de permissão para enviar mensagens.
3. Em **Actions → Radar Cripto → Run workflow**, escolha `main`. Marque `dry_run`
   para pesquisar sem envio; desmarcado usa os Secrets existentes.
4. Logs, `run.json`, `summary.txt` e `source-health.json` ficam nos artifacts,
   inclusive quando a pesquisa é parcial.

O resumo diário está agendado às **10h15 de Brasília** (`15 13 * * *`). Há novas
verificações às **16h15 e 22h15** (`15 19 * * *` e `15 1 * * *`) para alertas de
novidades/atualizações. O resumo não se repete no mesmo dia. GitHub Actions não é
servidor permanente e pode atrasar o início. Em repositórios públicos sem atividade,
o GitHub pode suspender agendamentos após 60 dias: acompanhe a aba Actions.

## Fontes reais, configuráveis

A lista em [`config/sources.json`](config/sources.json) contém 16 fontes:

- BitDegree LearnDrops, guild oficial BitDegree e catálogo público de missões;
- Ethereum Foundation, Chainlink, Optimism, Starknet e Solana;
- Arbitrum, Base, Polygon, ZKsync e Scroll;
- Binance Academy, OKX Rewards/Learn & Earn e Revolut Crypto Learn Rewards.

Arbitrum, Base e Scroll usam RSS descobertos nas páginas oficiais. Scroll usa o
CMS Ghost referenciado no conteúdo de `scroll.io/blog`. Os demais usam páginas
públicas com seletores explícitos. O leitor também suporta Atom e JSON com schema
configurado; **não foi inventado endpoint de API** para aumentar a lista.

`discovered_from` registra procedência. [`config/source_audit.json`](config/source_audit.json)
é a fotografia da auditoria de desenvolvimento, com HTTP, data, endereço final,
formato e resultado da extração. Não substitui o estado vivo: cada execução salva
`source-health.json` e histórico por fonte em `radar-state`, com última tentativa,
última coleta válida, status HTTP e próxima tentativa permitida.

Uma página HTTP 200 sem itens identificáveis não é contada como coleta válida.
Domínios são exatos e aprovados manualmente. Para fontes novas, verifique autoria,
formato, caminho e seletores antes de cadastrar. Agregadores e missões de usuários
não confirmam gratuidade ou recompensa por si só.

## Investigação das campanhas

Depois de ler a página individual, o radar segue até três links públicos de regras,
recompensas ou requisitos relacionados à mesma campanha, dentro de domínios oficiais
configurados. Não transforma termos genéricos de outra plataforma em regras da missão.
Se uma regra relacionada falhar, não anuncia custo zero com investigação incompleta.

A análise guarda URLs e trechos de evidência e verifica custo, recompensa, KYC,
Brasil, prazo e requisitos de conta. Uma rota gratuita alternativa só é aceita quando
as regras oficiais descrevem entrada completa sem compra/depósito e não há obrigação
financeira global. Staking/deposito opcionais não viram obrigação automaticamente.
Testnets precisam declarar faucet gratuito, tokens sem valor real e ausência de fundos
reais; uma exigência de depósito mainnet prevalece.

### BitDegree

A FAQ oficial é consultada e sua regra de missões gratuitas só é aplicada às tarefas
educacionais de missões verificadas. Isso não comprova saque, token ou prêmio.
A regra não remove depósitos obrigatórios nem custos de ações on-chain. Rounds de
ativação de cartão ou resgate de bônus continuam com custo não comprovado. Cashback
e bônus comerciais da exchange não são apresentados como prêmios da rota educacional.

O catálogo `/missions` contém conteúdo criado por usuários. Apenas guilds explicitamente
verificadas em `trusted_guilds` podem ser confirmadas nessa fonte; os demais anúncios
ficam **NÃO CONFIRMADOS**. A listagem LearnDrops e a guild oficial são consultadas
separadamente. Não se presume prazo aberto só porque a missão aparece numa página.

Bits e Degree são pontos/progresso interno. Sorteios, tokens, NFTs e créditos são
identificados separadamente. O radar nunca converte pontos em dinheiro sem uma taxa
oficial verificável e não divide pools para inventar ganho individual.

## Conclusões, custo e prioridade

Custo financeiro e conclusão são campos separados: uma atividade pode ter participação
sem custo e, ao mesmo tempo, recompensa incerta ou exigência de KYC.

| Conclusão | Interpretação |
| --- | --- |
| GRATUITA CONFIRMADA | Participação sem custo demonstrada por fonte oficial. |
| GRATUITA COM TAXA DE REDE | Existe gas/taxa de transação; não entra nos alertas de custo zero. |
| GRATUITA COM REQUISITO DE KYC | Participação gratuita exige identificação; requisito de privacidade destacado. |
| GRATUITA, MAS COM RECOMPENSA INCERTA | Sorteio, prêmio condicional ou pontos sem ganho cripto garantido. |
| PODE EXIGIR INVESTIMENTO | Regras insuficientes ou ambíguas. Continua sendo investigada. |
| EXIGE INVESTIMENTO | Compra, depósito, staking, saldo ou pagamento obrigatório. |
| ENCERRADA | Status ou prazo oficial indica encerramento. |
| NÃO CONFIRMADA | Falta confirmação oficial suficiente. |

O relatório inclui token/quantidade quando divulgados, natureza da recompensa, valor
anunciado verificável, possibilidade de saque/negociação declarada, início, encerramento,
países e restrições. Ticker não é prova de listagem ou saque. Nenhuma cotação é inventada.

O score pondera custo zero, esforço, fonte oficial, evidência de recompensa, Brasil,
prazo aberto e condições da conta. Só exibe prioridade alta, média ou baixa e score
comparativo; não inventa probabilidades numéricas de receber tokens. Missões de pontos,
sorteios e perfis ainda condicionados não recebem prioridade alta. KYC é identificação,
não investimento; Brasil desconhecido nunca é apresentado como confirmado.

## HTTP, limites e disponibilidade

- **429:** interpreta `Retry-After` em segundos ou HTTP-date; espera com backoff e
  jitter, limita a duas tentativas e registra cooldown por domínio. Se o tempo excede
  o orçamento, adia sem consultar antes do prazo. O cooldown persiste entre execuções.
- **202:** aceita como processamento pendente, sem fingir que recebeu campanhas.
  Guarda somente `Location` ou `Link rel=monitor` explicitamente fornecido e autorizado;
  consulta em execução posterior. Sem monitor, reconsulta a fonte depois da espera.
  Resultado pendente não é rotulado como falha definitiva.
- **5xx:** até três tentativas, backoff e jitter; depois adia e registra falha.
- **403/404:** registra indisponibilidade sem repetir a mesma requisição.
- Timeout de conexão/leitura, limite de 2 MB, até cinco redirecionamentos, HTTPS,
  validação de domínio/IP público, XML sem entidades e intervalo por domínio.

Cache em memória evita baixar a mesma FAQ várias vezes numa execução. Após três
falhas de verificação em uma fonte, suspende aquela verificação. Orçamento global
limita o trabalho. Restrições externas não são burladas para deixar o job verde.

## Histórico persistente e Telegram

O estado é salvo na branch **`radar-state`**, usando a permissão `contents: write`
do job de pesquisa. A branch principal não é alterada pelo bot. A versão 2 migra
automaticamente o estado v1 preservando hashes e resumos existentes; um único resumo
de migração v2 pode ser enviado no mesmo dia. Estado inválido não é apagado silenciosamente.

Todas as candidatas observadas são registradas, inclusive possíveis investimentos.
O radar detecta: nova oportunidade gratuita, confirmação de uma rota gratuita,
alteração de recompensa/prazo/custo e encerramento. Reconsulta em rotação até três
campanhas históricas ausentes da listagem por fonte e aplica prazos oficiais já salvos.
Não considera desaparecimento ou erro HTTP como prova de encerramento.

Resumo é enviado **primeiro**, seguido dos alertas novos/atualizados. Os destaques
do resumo também excluem campanhas inalteradas, evitando repetição diária de links. Uma alteração
não entregue permanece pendente. Marca entrega só após sucesso da API. Mensagens
em texto simples são divididas por unidades UTF-16 e respeitam rate limits.
POST com timeout é ambíguo e não é repetido imediatamente. Telegram e Git não têm
transação conjunta: uma interrupção depois da aceitação e antes de salvar pode causar
repetição; não há promessa de exatamente uma entrega em toda falha possível.

O estado público contém campanhas, evidências de regras resumidas em hashes/snapshots,
metadados das fontes e datas. Não contém token, chat ID, cookies ou dados de carteira.
Nenhum depósito, compra, transferência, assinatura ou conexão de carteira é executado.

## Quizzes: estudo autorizado

`src/quiz_analyzer.py` preserva leitura de perguntas em JSON ou HTML público estático,
consulta material oficial permitido e retorna alternativa provável, explicação,
confiança e citações. É recuperação lexical de apoio ao estudo, sem API paga: abstém
quando não há evidência ou a pergunta é negativa. Não promete compreensão semântica.

```bash
python -m src.quiz_analyzer config/quiz.example.json --output reports/quiz-results.json
```

Ajuste o exemplo para materiais públicos autorizados e cadastre seus domínios oficiais.
`question_pages` aceita `url`, `container_selector`, `question_selector` e `option_selector`.
**Não existe submissão automática**, login, CAPTCHA ou consulta a avaliações privadas.

## Testar e executar localmente

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
ruff check .
actionlint -shellcheck= .github/workflows/radar.yml
python -m compileall -q src scripts main.py
python scripts/check_secrets.py
python -m scripts.audit_sources
python -m src.main --dry-run
```

Os testes bloqueiam rede e simulam HTTP/Telegram; não enviam mensagens reais.
`--dry-run` pesquisa fontes reais sem enviar ou alterar o histórico. Para envio real,
forneça as duas variáveis de ambiente por meio seguro e execute `python -m src.main`.
`python main.py` continua compatível. Nenhuma dependência paga foi adicionada.

Saída `0`: sem erros detectados (pode haver fonte 202 pendente, indicada no relatório).
Saída `2`: cobertura/entrega parcial. Saída `1`: falha fatal. Um job vermelho pode já
ter enviado o resumo; entregas confirmadas são persistidas mesmo em falhas parciais.

Telegram 401/404: confira o token do BotFather sem URL/prefixo. 400/403: confira destino,
`/start` e permissões. Não envie tokens para pedir suporte. A coleta é heurística e
limitada às fontes públicas configuradas; não garante renda, elegibilidade pessoal ou
quantidade diária de oportunidades.

O ZIP inicial permanece preservado. Nenhum workflow antigo foi reintroduzido.
Resultados reais, limitações e mudanças estão em [`VALIDATION.md`](VALIDATION.md).
Os testes e a auditoria da versão 2 estão em [`VALIDATION_V2.md`](VALIDATION_V2.md).

## Radar 2.1 — estudo assistido de quizzes BitDegree

A etapa independente `src.bitdegree_quizzes` agora participa das mesmas verificações
programadas. O radar de airdrops, seus filtros, horários, relatórios e entregas continuam
no fluxo 2.0. A nova etapa usa os três hubs BitDegree já cadastrados em
`config/sources.json`: LearnDrops, guilda oficial e missões públicas. Guildas de usuários
só entram quando explicitamente confiáveis na configuração existente.

O monitor visita missões e links de estudo/quiz publicados na própria página; aceita
apenas domínios oficiais cadastrados, com validação HTTPS, DNS público e redirects.
Não inventa endpoints. Perguntas e alternativas são extraídas exclusivamente do HTML
público estático (`fieldset/legend/label` ou marcação `data-quiz-question`). Conteúdo
oculto, JSON de hidratação, formulários de login e gabaritos privados não são lidos.
Materiais de estudo excluem os formulários do quiz para impedir uma resposta de servir
como evidência de si mesma. Layouts diferentes exigem atualização do extrator.

Quando há perguntas, o Telegram recebe pergunta, alternativas, resposta provável,
justificativa, trecho de apoio, URL oficial, confiança e limitações. A busca lexical é
conservadora: exige frase de apoio e diferença entre alternativas; perguntas negativas,
alternativas semelhantes, evidências conflitantes ou insuficientes retornam **“não
determinado”**. Não há compreensão semântica completa nem garantia de acerto. A
confiança máxima automática é média; a revisão humana é necessária. A pesquisa usa
materiais públicos efetivamente vinculados à missão e domínios oficiais configurados,
sem busca geral na internet ou serviço de IA pago.

Quando nenhuma pergunta está pública, o bot informa isso e fornece o link da missão.
Não confunde ausência de HTML extraível com inexistência de quiz na plataforma e não
inventa respostas. Uma missão monitorada não constitui confirmação de gratuidade,
recompensa, prazo ou elegibilidade. Essa avaliação continua no radar 2.0.

O estado existente `radar-state/radar.json` ganhou apenas os campos `quizzes` e
`quiz_checks`, preservando a versão e todos os registros anteriores. São salvos hashes,
respostas, citações, última consulta e entrega confirmada. Conteúdo idêntico reutiliza a
análise; novas perguntas, alternativas ou respostas alteradas geram novo alerta. Falhas
de coleta preservam a análise anterior. Falhas de Telegram mantêm a entrega pendente.
Uma falha após envio parcial pode repetir partes na tentativa seguinte: a API não oferece
transação atômica para várias mensagens. O mesmo divisor UTF-16 do Telegram é usado.

Limites por execução: até 18 chamadas de coleta, seis missões, dois links relacionados
por missão e 12 perguntas por missão. O orçamento de 120 segundos é verificado entre
chamadas; uma requisição em andamento pode excedê-lo até seu timeout/retry. Reutiliza
os limites HTTP existentes (2 MB, timeout, redirects seguros e cooldown persistente),
com até duas tentativas, intervalo mínimo de um segundo e espera máxima local de cinco
segundos antes de adiar uma fonte. As missões são alternadas por última tentativa,
inclusive quando falham, para não bloquear a descoberta das demais.

```bash
# Coleta real, sem Telegram nem alterações no histórico
python -m src.bitdegree_quizzes --dry-run

# Usa os mesmos dois Secrets/variáveis já configurados
python -m src.bitdegree_quizzes
```

O relatório separado é `reports/bitdegree-quizzes.json`; erros fatais vão para
`reports/bitdegree-failure.json`. O workflow executa a etapa mesmo após falha parcial
do radar, desde que o histórico tenha sido restaurado, e persiste o estado ao final.
As execuções de push/PR continuam apenas validando o código. Não são necessários novos
Secrets ou dependências. Não há login, cookies de sessão, armazenamento de credenciais,
CAPTCHA, conexão de carteira ou submissão automática de respostas, mesmo se uma
plataforma passar a permiti-la: tal recurso não existe nesta implementação.

Validação e limites desta entrega: [`VALIDATION_V21.md`](VALIDATION_V21.md).

## Diagnóstico 2.2 — limites demonstrados

A auditoria individual das seis missões está em
[`docs/bitdegree-v22-diagnostic.json`](docs/bitdegree-v22-diagnostic.json).
Todas entregaram resumo e nomes de rodadas, com uma aplicação `missions-mount` /
`dashboard-layout`; não havia perguntas no HTML nem JSON de quiz incorporado.
Isso demonstra ausência no documento recebido, **não** prova exigência de login.
A inspeção renderizada não pôde ser concluída por limite do navegador deste ambiente.
Não foram consultadas rotas internas nem simulada participação para obter perguntas.

A etapa agora registra diagnóstico, status HTTP, tipo de conteúdo e contagens por missão,
inclusive em falhas técnicas. Foram adicionados formatos públicos explícitos de questão
única, múltipla e escrita, e JSON de Quiz explicitamente público. Estes formatos novos
foram validados com exemplos artificiais; nenhum foi encontrado nas seis missões reais.
Questões escritas e de múltiplas respostas ficam inconclusivas: não há inferência validada
para determinar a resposta completa. HTML/JSON promocional e FAQ não viram perguntas.
Nenhuma API dinâmica foi adicionada: não foi encontrada documentação oficial de uma
API pública de perguntas. Não se extrai conteúdo de rotas internas ou hidratação arbitrária.

O CLI de produção envia apenas resultados com perguntas públicas, mantendo histórico
de diagnósticos sem alertas vazios. A API Python mantém o comportamento de notificação
de diagnóstico 2.1 por compatibilidade; `notify_diagnostics=False` aplica a regra nova.

Para reproduzir a auditoria de extração, sem envio e sem análise de respostas:

```bash
python -m scripts.diagnose_bitdegree --output reports/bitdegree-diagnostic.json
```

A coleta e análise de quizzes reais permanece **não demonstrada**; não há respostas
reais produzidas. Detalhes e limites em [`VALIDATION_V22.md`](VALIDATION_V22.md).

## 2.3 — análise autenticada bloqueada pelos termos

A [seção 10 dos termos oficiais](https://www.bitdegree.org/terms-of-service) proíbe
cópia por tecnologia de robôs/crawlers. Seguindo o requisito de interromper quando a
plataforma proibir esse acesso, a coleta autenticada não foi habilitada. É necessária
uma autorização específica da BitDegree para reavaliar essa integração.

`python -m scripts.bitdegree_login` apenas explica o impedimento e sai com código 2:
não abre Chromium, não solicita senha e não salva sessão. Não é um login funcional.
Não configure `BITDEGREE_STORAGE_STATE_B64` nem envie cookies para esta integração.
A pasta `.auth/` está preventivamente ignorada pelo Git; não deve integrar artifacts,
relatórios ou fixtures. Não há sessão importada ou expirada a renovar nesta versão.

`python -m src.bitdegree_authenticated` registra o bloqueio para cada uma das seis
missões em `reports/bitdegree-authenticated.json`. Nenhum Secret é lido. Essa etapa
retorna 0 para permitir que o radar continue, com status explícito de **não executada**.
O workflow inclui esse registro sem instalar navegador ou transmitir sessão. Os fluxos
anteriores permanecem preservados; não há alegação nova de autorização desses fluxos.

Login, validade/expiração de sessão, leitura dinâmica e iframes autenticados continuam
não implementados nem testados em conta real. Os 252 testes aprovados verificam o
código existente e o bloqueio novo; não demonstram acesso autenticado.
Veja [`VALIDATION_V23.md`](VALIDATION_V23.md).

## 2.4 — multiplataformas com permissões auditadas

O cadastro central é `config/platforms.json`: Binance, CoinMarketCap, Galxe, Layer3,
Zealy, Intract, QuestN, Revolut e a barreira BitDegree. Contém links oficiais, termos,
documentação, data de auditoria, método permitido, limitações, tipos de recompensa e
habilitação individual. A pesquisa dos termos foi manual; uma página pública não
habilita scraping. Termos inacessíveis permanecem como limitação, não aprovação.

Há APIs documentadas de Galxe e Zealy, com acesso específico de projeto/admin.
Somente o conector GET da Zealy foi implementado: até três comunidades administradas
pelo dono da chave, sem claims, 1 segundo de intervalo, até duas tentativas, limites
HTTP existentes e cooldown persistente. A documentação inclui integrações no plano
gratuito. Não é uma API de busca global nem concede acesso a comunidades de terceiros.
Para usá-la, cadastre seus subdomínios em `communities` da Zealy e um GitHub Secret
`ZEALY_API_KEY` com chave de **somente leitura**. Sem isso, a fonte é ignorada e as
outras continuam. Não há cobrança contratada nem necessidade desse Secret para o radar.

Galxe permanece sem coletor: token, escopo e disponibilidade de acesso gratuito não
foram validados para esta conta. A API de mercado da CoinMarketCap não foi tratada
como API de campanhas. Não existem endpoints inventados de quizzes ou de campanhas.
A autorização GET da Zealy expira no código após 30 dias da auditoria: revise a evidência
antes de atualizar a data no cadastro; a data isolada não cria uma permissão nova.

Os caminhos antigos de coleta BitDegree, Binance L&E e Revolut foram desativados em
`config/sources.json`. O HttpClient também bloqueia sites das nove plataformas e
redirecionamentos para eles, exceto o GET documentado da Zealy. Isso fecha a coleta
legada sem auditoria; os módulos anteriores continuam disponíveis e seus testes foram
preservados. A BitDegree não é consultada novamente, mesmo pelo script de diagnóstico.
As demais fontes do radar continuam funcionando. Não há login, cookies de sessão,
carteiras ou transações. O cliente novo rejeita cookies do servidor.

`config/campaign_observations.json` contém **observações reais de pesquisa manual**,
com evidência oficial e data, não uma descoberta automatizada. Foram encontrados:

- Bitcoin Basics, Binance: anuncia 0.00001 BTC para novos usuários, limite de 5.000 por
  mês e KYC conforme FAQ. Brasil, cota atual e todas as obrigações financeiras não
  comprovados: `GRATUIDADE_NAO_CONFIRMADA`, disponibilidade não confirmada.
- Campanha Binance de volume de negociação: exige volume mínimo de US$ 10.000 para
  compartilhar um pool anunciado. `EXIGE_CAPITAL`; não é dinheiro gratuito.

Observações manuais vencem para novos alertas em sete dias; não são reconsultadas por
scraping. O Telegram identifica sua data e limitações, informa custo, taxas, Brasil,
requisitos, recompensa e permissão. Não reapresenta inalteradas; mudanças relevantes e
encerramentos conhecidos de campanhas já notificadas podem gerar alertas. Datas de
revisão isoladas não geram repetição. Nenhuma campanha fictícia entra na configuração.

A classificação financeira exige regras oficiais completas e ausência comprovada das
obrigações de depósito, compra, staking pago, NFT pago, assinatura, inscrição e gas
para `ZERO_INVESTIMENTO`. Gas fica separado; KYC não é investimento. Pontos, badges,
certificados e créditos não são tokens sacáveis. Sorteios e pools não garantem pagamento
individual. Regras desconhecidas não viram gratuidade. Não há conversão financeira
estimada de pontos. Brasil não elegível e campanhas encerradas recebem prioridade baixa.

A análise de quizzes reutiliza os módulos existentes e exige tanto permissão de acesso
quanto autorização específica de análise. Nenhuma das plataformas auditadas foi habilitada
para coletar perguntas automaticamente. Não foram encontradas perguntas reais extraíveis
por um meio automatizado autorizado. Listagem de quests de uma API não comprova regras,
recompensas oficiais do projeto ou ausência de custo, e não gera sozinha alerta financeiro.

```bash
python -m src.multiplatform --dry-run
# Envio com as mesmas variáveis Telegram já existentes:
python -m src.multiplatform
```

A etapa participa do workflow existente antes da persistência de estado. O histórico
`radar-state/radar.json` mantém os registros anteriores e adiciona `platform_campaigns`
e `platform_health`. O relatório é `reports/multiplatform.json`; o estado da fonte
contém última execução, HTTP real quando houve, erros, catálogos e limitações.

**Resultado desta entrega:** 0 oportunidades zero investimento verificadas, 0 chamadas
à API sem chave/admin configurado e 0 perguntas reais extraídas. A descoberta contínua
ampla ainda não está disponível: as permissões e acessos encontrados não autorizam
scraping geral das plataformas. Ver [`VALIDATION_V24.md`](VALIDATION_V24.md).

## Radar 2.5

O relatório multiplataforma separa campanha anunciada, estoque de recompensa, acesso
brasileiro e resgate. A análise de novembro do Bitcoin Basics está em
[VALIDATION_V25.md](VALIDATION_V25.md). O Telegram mostra primeiro as oportunidades
verificadas por pontuação. Quando a lista está vazia, envia um aviso diário e mantém
as campanhas pendentes no relatório JSON.

A classificação financeira verifica separadamente depósito, compra, volume de
trading, staking, NFT pago, assinatura, inscrição, resgate e gas. KYC e cadastro
são requisitos de elegibilidade. Um voucher anunciado só entra no alerta se houver
evidência de resgate, disponibilidade atual e elegibilidade no Brasil.

### Galxe

Para um Space ao qual você tem acesso autorizado, configure o ID numérico em
`space_ids` da entrada Galxe em `config/platforms.json`. Use um token emitido
no painel Galxe para esse acesso e guarde-o no GitHub Actions Secret
`GALXE_ACCESS_TOKEN`. Use apenas acesso já autorizado com custo compatível.
Sem token ou Spaces, o conector registra a execução como ignorada.
[Autenticação oficial](https://docs.galxe.com/galxe-integration/getting-started/authentication).

O conector lista a primeira página de até 20 quests em cada um de até três Spaces,
consulta detalhes das duas primeiras por Space e indica quando a listagem é parcial.
Ele usa o endpoint GraphQL oficial, com consultas fixas de leitura e limite de uma
requisição por segundo. Respostas 401 e 403 encerram a consulta da fonte. Respostas
429 adiam novas consultas, com espera persistida nas execuções agendadas.
[Referência de quests](https://docs.galxe.com/galxe-integration/api-reference/quest) e
[limites da API](https://docs.galxe.com/galxe-integration/resources/rate-limits).

Datas, status, capacidade, pontos e gas são metadados do catálogo. Valores
financeiros, regras completas, país e quizzes permanecem pendentes quando a resposta
da API não os comprova. A consulta de elegibilidade por endereço fica fora do catálogo.

A leitura Zealy continua restrita ao GET oficial de comunidades administradas.
Use chave somente leitura em `ZEALY_API_KEY` para esse endpoint. As observações
públicas manuais funcionam sem chaves Galxe ou Zealy.
[Documentação Zealy](https://docs.zealy.io/api-reference/quests/list-quests).

## Radar 2.6

O relatório registra URL, status HTTP e horário por fonte quando há resposta das
APIs. As campanhas de catálogo conservam a origem e o horário de consulta.
A ausência de credencial ou de escopo configurado aparece como execução ignorada.
A Galxe sinaliza listagens parciais quando a API informa páginas adicionais.
A Zealy continua limitada às comunidades autorizadas do cadastro.

`financial_classification` descreve os custos. `opportunity_status` só recebe
`GRATUITA_CONFIRMADA` com evidência oficial recente, recompensa financeira
resgatável, disponibilidade, Brasil confirmado e investimento inicial zero.
Sorteios ficam fora dos alertas. Quando a lista está vazia, o Telegram informa
“Nenhuma oportunidade que atenda a todos os critérios de gratuidade e resgate foi confirmada nesta execução.”

A auditoria de novembro e o resultado da execução estão em [VALIDATION_V26.md](VALIDATION_V26.md).

## Radar 2.7

1. **Galxe.** No painel oficial, abra Settings → Server API → Generate New API
   Tokens. Use um token autorizado a consultar as quests dos Spaces escolhidos
   e selecione somente leitura, se o painel oferecer esse escopo. Cadastre
   `GALXE_ACCESS_TOKEN` e informe em `config/platforms.json` os IDs numéricos
   dos seus Spaces autorizados no campo `space_ids` da entrada Galxe.
   [Autenticação Galxe](https://docs.galxe.com/galxe-integration/getting-started/authentication).
2. **Zealy.** Nas configurações da comunidade administrada, crie uma chave
   **read-only**. O endpoint exige papel de administrador na comunidade.
   Cadastre `ZEALY_API_KEY` e informe no campo `communities` da entrada Zealy
   os subdomínios autorizados. Cada subdomínio é o trecho após `/cw/` na URL.
   [Autenticação Zealy](https://docs.zealy.io/authentication) e
   [endpoint de quests](https://docs.zealy.io/api-reference/quests/list-quests).
3. **GitHub.** No repositório, abra Settings → Secrets and variables → Actions →
   New repository secret. Cole cada valor no formulário do Secret correspondente.
   Mantenha os valores no formulário do GitHub. Os identificadores de escopo vão
   no cadastro, sem credenciais.
4. **Conexão.** Abra Actions → Radar Cripto → Run workflow, selecione `main` e
   marque `dry_run`. Confira o log da etapa de plataformas e o artefato
   `reports/multiplatform.json`. Com escopos e credenciais autorizados, o teste
   faz consultas reais de leitura e registra horário, endpoint, HTTP e resultados.
   O dry-run desabilita envio ao Telegram e alteração do histórico.

O diagnóstico da `main` indica se cada credencial está disponível para o runner
e se há escopo no cadastro. Respostas 401, 403, 429, falhas genéricas e catálogos
vazios têm mensagens próprias. O relatório habitual do Telegram inclui esse
diagnóstico e mantém as oportunidades pendentes apenas no JSON.

## Radar 2.8

1. Obtenha acesso somente aos Spaces que você pode consultar na Galxe. No
   painel oficial, abra Settings → Server API → Generate New API Tokens.
   Use o menor escopo disponível para consultas. A integração usa apenas
   queries GraphQL fixas. [Autenticação Galxe](https://docs.galxe.com/galxe-integration/getting-started/authentication).
2. Na Zealy, use as configurações de uma comunidade que você administra e
   selecione uma chave **read-only**. A API exige acesso administrativo
   à comunidade para listar quests. [Autenticação Zealy](https://docs.zealy.io/authentication)
   e [listagem de quests](https://docs.zealy.io/api-reference/quests/list-quests).
3. No repositório, abra **Settings → Secrets and variables → Actions →
   New repository secret**. Cadastre `GALXE_ACCESS_TOKEN` e `ZEALY_API_KEY`
   diretamente no GitHub.
4. Em `config/platforms.json`, preencha `space_ids` e `communities` nas
   entradas correspondentes da lista `platforms`. A seção
   `configuration_examples` é apenas ilustrativa. Após selecionar uma chave
   Zealy somente leitura no painel, declare `read_only_key: true` no JSON
   da entrada Zealy. Essa declaração registra a configuração feita pelo
   operador. A API de listagem não verifica o escopo da própria chave.
5. Execute **Actions → Radar Cripto → Run workflow** em `main` com
   `dry_run` marcado. Verifique o diagnóstico e `reports/multiplatform.json`.
   Com credencial e escopo válidos, o dry-run executa as consultas reais de leitura.
   O teste de conexão não envia mensagens. As execuções normais incluem um
   bloco para cada plataforma no relatório do Telegram.

Cada conector aceita até três escopos sem duplicatas. A Galxe informa cobertura
parcial quando encontra páginas adicionais. A Zealy retorna uma lista no endpoint
documentado e sinaliza corte local acima de 50 entradas por comunidade.
Tipos de recompensa, tarefas e condições observados são metadados do catálogo.
A confirmação de custo zero, acesso brasileiro e resgate depende de evidência
oficial adicional. Veja [VALIDATION_V28.md](VALIDATION_V28.md).
