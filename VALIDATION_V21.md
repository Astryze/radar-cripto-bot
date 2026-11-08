# Radar Cripto 2.1 — BitDegree público

Base preservada: `06d65f27ff81e39397cb2adb6590097d49fc5174` (versão 2.0).
Data: 08/11/2026 UTC. Nenhum arquivo removido; nenhuma dependência adicionada.

## Alterações

- `src/bitdegree_quizzes.py`: descoberta nos hubs existentes, leitura pública de missões
  e materiais vinculados, orçamento de coleta, cache versionado, alternância de missões,
  relatório separado e entrega pelo Telegram com deduplicação.
- `src/quiz_analyzer.py`: extrator compartilhado de perguntas públicas, remoção de
  conteúdo oculto/login e formulários dos materiais; abstenção em perguntas negativas,
  alternativas similares, negativas ou abrangentes, evidências fracas e contraditórias;
  opções, justificativa, trecho, URL, confiança e limitações em cada resultado.
- `src/state.py`: dois campos opcionais (`quizzes`, `quiz_checks`), sem apagar ou
  reinterpretar os registros de campanhas, resumos e entregas da versão 2.0.
- `.github/workflows/radar.yml`: etapa independente após o radar e antes de persistir
  o histórico, inclusive com falha parcial anterior; respeita dry-run e restauração.
- `tests/test_bitdegree_quizzes.py`: testes offline novos, sem serviços externos.
- `README.md` e este documento: execução, arquitetura e limites reais.

## Verificações

Os 189 testes existentes passaram antes das alterações. Após a implementação,
**233 testes passaram**: os 189 originais e 44 novos. Nenhum teste existente removido
ou alterado. A fixture global bloqueia requisições de rede em todos os testes.

Verificações executadas: `python -m pytest -ra`, `ruff check .`,
`python -m compileall -q src scripts main.py`,
`actionlint -shellcheck= .github/workflows/radar.yml`, leitura YAML e
`python scripts/check_secrets.py`. A varredura por padrões não detectou credenciais
no código ou no ZIP original; não constitui auditoria exaustiva de segredos.

Cobertura nova: descoberta, fonte não confiável, links e redirects indevidos, análise,
material oficial relacionado, remoção de perguntas dos materiais, conteúdo oculto e
hidratação, login, negativas, alternativas semelhantes, contradições, inconclusão,
cache, atualizações de perguntas/alternativas/evidências, reenvio após erro, preservação
do histórico, falhas transitórias, ausência pública, rodada justa inclusive em falha,
limites de coleta, tipo de conteúdo, dry-run, CLI, cookies rejeitados e mensagens longas.
Os testes existentes continuam verificando HTTP 202/429/403/404/5xx, retry/backoff,
Retry-After, Telegram e persistência Git.

## Serviços reais e limites

LearnDrops, guilda oficial e missões públicas responderam com HTML; a descoberta real
identificou 34 missões candidatas. Algumas missões antigas redirecionam à página geral
da guilda: agora esses casos são recusados, sem atribuir perguntas de outra campanha.
As páginas inspecionadas não expuseram perguntas/alternativas extraíveis no HTML
público. Não há gabarito real produzido nem demonstração de resolução de quiz privado.
A lógica de análise e envio está validada com fixtures offline explicitamente artificiais,
nunca apresentadas como campanhas ou respostas reais no relatório de produção.

O diagnóstico local de páginas reais usou o proxy do ambiente, que não fornece DNS
direto. A validação DNS foi desativada **apenas nesse harness temporário fora do
repositório**, mantendo HTTPS e allowlist; o código publicado conserva a proteção DNS
integral. O diagnóstico foi dry-run e não enviou Telegram nem alterou o estado persistente.

O monitor não promete acesso a material protegido ou dinâmico, busca semântica geral,
acerto garantido ou descoberta de toda a plataforma. Nunca consulta APIs privadas,
respostas ocultas, login ou CAPTCHA. Não possui submissão de avaliações. Materiais
não disponíveis publicamente ficam para revisão manual. Nenhum cookie ou credencial
é salvo no histórico; o cliente público rejeita cookies do servidor.
