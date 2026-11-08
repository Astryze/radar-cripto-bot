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
A regra não remove depósitos obrigatórios nem custos de ações on-chain.

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

Resumo é enviado **primeiro**, seguido dos alertas novos/atualizados. Uma alteração
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
