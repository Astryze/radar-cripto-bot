# Validação — Radar Cripto 2.0

Data: 08/11/2026. Código-base preservado: `059c98e8b318da8dbda905137998b34ce0acb5ce`.

## Verificações locais

- Python 3.12.14 e dependências gratuitas já existentes; nenhuma dependência nova.
- **184 testes aprovados**, todos offline, com bloqueio de rede e mocks HTTP/Telegram.
- Ruff sem problemas; `compileall` sem erros; parsing YAML e actionlint aprovados.
- Varredura de credenciais sem achados nos arquivos e no ZIP inicial.
- Migração v1→v2, preservação de entregas, fila de transições, fechamento por prazo,
  recompensas/prazos alterados e integração Git da branch de estado testados.
- Novos testes para Retry-After em segundos/data, jitter, 429 com cooldown persistente,
  202 com/sem monitor, 403/404 sem repetição, 5xx com limite, HTTP JSON e telemetria.
- Investigação de regras, rota gratuita alternativa, obrigação global, KYC, Brasil,
  tokens/pools, pontos internos, testnet e confiança de guilds testados.
- Resumo antes dos alertas, não repetição, falha de entrega e mensagens de incerteza testados.

## Coleta real de desenvolvimento

A auditoria acessou as **16 fontes** configuradas com HTTP 200 e extraiu itens em
todas. Essa é uma fotografia no ambiente de desenvolvimento, não uma promessa de
disponibilidade no GitHub. Arbitrum e Base tiveram RSS declarado em `link rel=alternate`;
o CMS Scroll Ghost aparece no conteúdo de `scroll.io/blog` e declara seu RSS.
Nenhum endpoint de API foi presumido ou criado por tentativa.

Na pesquisa real completa da implementação, antes dos últimos ajustes de apresentação:
**12 candidatas**, **4 com participação gratuita comprovada**, **1 delas com prazo
aberto confirmado**. As quatro correspondem a atividades educacionais com pontos ou
recompensa incerta, não quatro pagamentos garantidos. Uma campanha estava encerrada.
Uma página Polygon excedeu o limite de 2 MB e não foi aceita. O relatório terminou
com código 2 por essa verificação parcial; o limite de segurança foi preservado.

As páginas e respostas usadas eram reais. Mocks foram usados apenas na suíte de
testes. Nenhum relatório do diagnóstico local foi enviado ao Telegram.

DNS direto não está disponível neste ambiente; o diagnóstico HTTP usou o proxy de
desenvolvimento por um harness temporário externo, mantendo HTTPS e lista de domínios
e omitindo apenas a resolução DNS local. A proteção de IP público permanece no código
entregue. A auditoria identifica essa condição em `transport`.

## Limites que continuam explícitos

- Pontos, créditos e NFTs não são automaticamente tokens negociáveis ou dinheiro.
- Participação sem custo não comprova elegibilidade pessoal, saque ou pagamento.
- Página pendente 202 não é resultado disponível. Cooldowns não burlam limitações.
- Missões de usuários da BitDegree não são campanhas oficiais por estarem hospedadas
  no mesmo domínio. Identidades precisam de confirmação.
- Uma regra que não pôde ser consultada pode manter a classificação como possível custo.
- Os alertas são disparados nas execuções diárias/manuais e verificações extras, não
  por monitoramento contínuo de servidor.
- Interrupções entre aceitação do Telegram e gravação do Git ainda podem causar
  repetição; não há transação distribuída nem promessa de exatamente uma entrega.

## Arquivos da versão 2

Alterados: `src/models.py`, `src/utils.py`, `src/feed_reader.py`, `src/bitdegree.py`,
`src/opportunity_filter.py`, `src/scoring.py`, `src/state.py`, `src/main.py`,
`src/telegram_bot.py`, `config/sources.json`, `config/README.md`, `README.md`,
`.github/workflows/radar.yml` e `tests/test_security_http.py`.

Criados: `src/investigation.py`, `scripts/audit_sources.py`, `config/source_audit.json`,
`tests/test_http_v2.py`, `tests/test_investigation.py`, `tests/test_history_v2.py`,
`tests/test_pipeline_v2.py`, `tests/test_sources_v2.py`, `tests/test_v2_regressions.py`
e este documento. Nenhum arquivo operacional foi removido.

O módulo de quizzes, os scripts de persistência/segredos, os nomes e valores dos
Secrets, a branch de histórico e o ZIP inicial foram preservados.
