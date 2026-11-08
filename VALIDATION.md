# Validação da implementação — 08/11/2026

## Verificações executadas

- Python 3.12.14; dependências instaladas de `requirements-dev.txt`.
- `python -m pytest`: suíte offline com mocks, incluindo integração local da branch
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
