# Validação da implementação — 08/11/2026

## Verificações executadas

- Python 3.12.14; dependências instaladas de `requirements-dev.txt`.
- `python -m pytest`: **123 testes aprovados**, suíte offline com mocks, incluindo integração local da branch
  de histórico com um repositório Git bare temporário. Nenhuma mensagem real nos testes.
- `ruff check .`: sem problemas.
- `python -m compileall -q src scripts main.py`: sintaxe Python válida.
- `actionlint -shellcheck= .github/workflows/radar.yml`: workflow válido. O lint de
  shell externo ShellCheck foi desabilitado por não estar disponível no ambiente.
- Parsing YAML e invariantes do cron, Python, Secrets e workflow único nos testes.
- `python scripts/check_secrets.py`: nenhuma credencial reconhecida nos arquivos
  atuais ou no conteúdo do ZIP original. A varredura é preventiva, não prova matemática
  de ausência de todo formato possível de segredo.

Cobertura: RSS/Atom, datas antigas/futuras, HTML falso, XML com entidades, domínio,
DNS privado, redirecionamento, limite de conteúdo, retries/timeout, filtros contextuais,
depósito/compra/staking/NFT/saldo/assinatura, requisitos opcionais, KYC, Brasil,
campanhas encerradas/pausadas, pontos internos, scoring, deduplicação, falha Telegram,
UTF-16/emoji, rate limit, estado persistente, dry-run e leitura pública de perguntas.

## Diagnóstico das fontes públicas

Foi executada uma coleta real em modo sem envio, com sete fontes: BitDegree,
Ethereum Foundation, Chainlink, Optimism, Starknet, Solana e Binance Academy.
Ao final: sete listagens/feeds acessíveis, nenhuma falha HTTP de verificação,
três candidatas após filtro contextual, nenhuma com gratuidade suficientemente
comprovada pelas regras públicas consultadas. Uma estava encerrada. Nenhuma foi
anunciada como oportunidade gratuita.

O diagnóstico encontrou e corrigiu duas situações reais: o antigo RSS da Chainlink
redirecionava para HTML, e os links relativos da Binance precisavam ser resolvidos
com base no domínio final do redirecionamento. Regressões incluem esses casos.
Os resultados são uma fotografia da consulta, não garantia de conteúdo futuro.

**Limitação do ambiente de desenvolvimento:** DNS direto não está disponível aqui;
o acesso HTTP externo ocorre por proxy. A execução normal de `--dry-run` registrou
essa falha de DNS, sem contornar a política de segurança do programa. Para o diagnóstico
externo foi usado um harness temporário fora do projeto, omitindo somente a consulta
DNS local e mantendo HTTPS/domínio. A política de IP público continua ativa no código
entregue e é testada com mocks; execução completa com DNS normal depende do runner.

## O que não foi comprovado nesta validação local

- Credenciais e entrega **real** no Telegram: Secrets não são lidos pelo conector
  GitHub. A suíte de envio é inteiramente simulada.
- O disparo diário futuro, que depende do agendador GitHub, Secrets válidos e
  permissões de Actions/branch. Testes do workflow não equivalem a uma entrega real.
- Campanhas que só revelam regras depois de login, CAPTCHA ou JavaScript privado.
- Ganhos, cotação de tokens, resgate ou elegibilidade pessoal: não são inferidos.

## Primeira execução real no GitHub

Após publicação, os 120 testes e demais checks passaram no runner GitHub. Foi
disparada também uma execução com os Secrets existentes, sem consultar seus valores.
Cinco fontes responderam normalmente; Solana retornou HTTP 429 e Binance HTTP 202.
O Telegram recusou o resumo com HTTP 404. A execução terminou corretamente com
código 2 e salvou logs/relatório como artifact, sem marcar resumo falho como entregue.

Essa execução motivou a normalização de espaços e quebras de linha nas extremidades
dos Secrets, validação contra injeção de caminho no token e mensagem de diagnóstico
específica para HTTP 401/404. Falhas externas não são escondidas para deixar o job verde.

## Segunda execução real

Os 122 testes da correção passaram também no runner GitHub. A segunda execução real
confirmou o funcionamento da coleta nas cinco primeiras fontes e a eliminação do
HTTP 404 após normalização do token. O Telegram respondeu HTTP 400, sem confirmação
de entrega. É necessário conferir `TELEGRAM_CHAT_ID` e iniciar a conversa com `/start`
(ou permissões do bot no grupo); os valores dos Secrets não foram lidos ou alterados.
Não houve entrega confirmada para persistir na branch de histórico.

Solana continuou retornando HTTP 429 e Binance HTTP 202 a partir do runner. Não foram
contornados bloqueios, login ou limites. O workflow corretamente terminou como falha
parcial, mantendo os artifacts. Uma nova execução com as mesmas configurações não
é apresentada como solução para essas recusas.

Referências:
- Validação inicial: https://github.com/Astryze/radar-cripto-bot/actions/runs/42525985066
- Primeira pesquisa real: https://github.com/Astryze/radar-cripto-bot/actions/runs/42526042975
- Segunda pesquisa real: https://github.com/Astryze/radar-cripto-bot/actions/runs/42526267348

A última melhoria adiciona diagnóstico seguro para erros conhecidos do Telegram
(incluindo chat não encontrado), sem registrar mensagens livres que possam expor dados.
Foi validada localmente com 123 testes e os mesmos checks de sintaxe/YAML/segredos.

## Envio confirmado após configuração do destino

Após atualizar o Secret de destino e o usuário iniciar a conversa com o bot,
a reexecução confirmou a entrega do resumo ao Telegram em 08/11/2026. Não houve
falha Telegram. A branch `radar-state` foi criada e registrou o resumo desse dia,
com persistência e upload dos artifacts concluídos com sucesso.

A pesquisa permaneceu parcial: cinco fontes consultadas, Solana com HTTP 429 e
Binance com HTTP 202. Foram classificadas três candidatas e nenhuma gerou alerta
de gratuidade confirmada. O código de saída 2 reflete essas duas falhas de fonte,
não falha de entrega. O agendamento diário continua em 10h15 de Brasília.

Comprovante: https://github.com/Astryze/radar-cripto-bot/actions/runs/42526870517/attempts/2
Nenhum ID pessoal ou valor de Secret foi acrescentado aos arquivos do projeto.

## Inventário exato de alterações

**Alterado:** `README.md`.

**Removidos:** `.github/workflows/blank.yml`, `.github/workflows/main.yml`, `radar.yml`.
Motivos e substituição documentados no README. Nenhuma funcionalidade operacional
do radar existia nesses workflows: o template só imprimia exemplos, um arquivo estava
vazio e o terceiro estava fora da pasta de workflows.

**Preservado sem modificação:** `radar-cripto-bot-inicial.zip`.

**Criados:**

```text
.github/workflows/radar.yml
.gitignore
VALIDATION.md
config/README.md
config/quiz.example.json
config/sources.json
main.py
pyproject.toml
requirements.txt
requirements-dev.txt
scripts/check_secrets.py
scripts/state_sync.py
src/__init__.py
src/bitdegree.py
src/feed_reader.py
src/main.py
src/models.py
src/opportunity_filter.py
src/quiz_analyzer.py
src/scoring.py
src/state.py
src/telegram_bot.py
src/utils.py
tests/conftest.py
tests/test_config_workflow.py
tests/test_feeds.py
tests/test_filters.py
tests/test_news_regressions.py
tests/test_quiz.py
tests/test_regressions.py
tests/test_scoring.py
tests/test_security_http.py
tests/test_state_main.py
tests/test_state_sync.py
tests/test_telegram.py
```
