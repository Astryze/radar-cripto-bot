# Radar Cripto

Radar gratuito de campanhas públicas, com Python 3.12, GitHub Actions e Telegram.
Prioriza participação sem investimento inicial. Consulta páginas reais, analisa
regras, conserva evidências e não inventa campanhas ou pagamentos.

## Colocar para executar

1. Abra **Settings → Secrets and variables → Actions** e cadastre
   `TELEGRAM_BOT_TOKEN` e `TELEGRAM_CHAT_ID`. Preserve os valores existentes, caso
   já estejam configurados. Nunca publique credenciais no código.
2. No Telegram, abra uma conversa com seu bot e envie `/start`. Para grupos,
   adicione o bot com permissão de envio e use o ID do grupo.
3. Abra **Actions → Radar Cripto → Run workflow**, branch `main`.
   `dry_run` desmarcado envia ao Telegram; marcado apenas pesquisa e gera artifacts.
4. Confira os jobs e o artifact `radar-logs-...`, disponível também em falhas parciais.

Agendamento: `15 13 * * *`, **10h15 de Brasília**, diariamente. O GitHub pode atrasar
o início. Não é servidor permanente. O workflow deve estar na branch padrão.
Em repositórios públicos sem atividade, o GitHub pode suspender agendamentos após
60 dias: confira Actions se os relatórios pararem.

O job de pesquisa usa `contents: write` para persistir histórico em `radar-state`.
Se a política de Actions/organização impedir, permita a criação/escrita dessa branch.
O bot não altera o código em `main`.

## Relatórios

- Alertas novos/atualizados: somente **GRATUITA CONFIRMADA**, fonte oficial consultada,
  prazo aberto e sem exclusão explícita do Brasil. Elegibilidade desconhecida é
  informada; não é apresentada como participação brasileira garantida.
- Um resumo por dia de Brasília: total analisado, gratuitas, gas, investimento
  obrigatório, possíveis custos, não confirmadas, indisponíveis e falhas de cobertura.
- Cada alerta inclui campanha, projeto/fonte, recompensa e natureza, custo, esforço,
  prioridade, Brasil, KYC, prazo, confirmação, passos, evidência e link oficial.

`reports/run.json` inclui todas as campanhas classificadas, inclusive as rejeitadas
dos alertas gratuitos. Uma coleta falha não vira prova de ausência de oportunidades.
Reexecuções no mesmo dia podem alertar mudanças sem repetir o resumo já entregue.

## Classificação conservadora

| Classificação | Evidência necessária |
| --- | --- |
| GRATUITA CONFIRMADA | Regras oficiais declaram participação gratuita ou ausência de compra/depósito; nenhuma obrigação financeira ou ambiguidade detectada. |
| GRATUITA COM TAXA DE REDE | Participação gratuita declarada e custo explícito de gas/rede, sem outra obrigação financeira detectada. |
| PODE EXIGIR INVESTIMENTO | Regras oficiais incompletas, custos ambíguos ou operação on-chain sem explicação suficiente das taxas. |
| EXIGE INVESTIMENTO | Depósito, compra, staking, saldo mínimo, NFT, assinatura ou pagamento obrigatório detectado. |
| NÃO CONFIRMADA | Agregador ou página oficial sem verificação suficiente. |

“Free”, “airdrop” e “rewards” isolados não comprovam gratuidade. Staking opcional
não vira obrigação. KYC é identificação/privacidade, não investimento. Não se presume
Brasil elegível por falta de restrições. Publicação recente não comprova prazo aberto.
Campanhas com gas ou investimento obrigatório não geram alertas de investimento zero.

Recompensa confirmada significa descrição encontrada na fonte, **não pagamento
individual garantido**. Sorteio/linguagem condicional recebe indicação de estimativa.
Bits, Degree e pontos internos não são convertidos em dinheiro ou tokens negociáveis.
Pools não são divididos para inventar ganho pessoal.

Pontuação: até 45 por custo zero, 15 por esforço baixo, 10 pela fonte oficial,
10 por recompensa descrita, 10 por prazo aberto e 10 por Brasil confirmado.
Prioridade alta exige todas essas condições. Encerradas, pausadas ou excluídas
do Brasil não entram nas melhores oportunidades disponíveis.

## Fontes

Edite [`config/sources.json`](config/sources.json). Fontes iniciais: BitDegree,
Ethereum Foundation, Chainlink, Optimism, Starknet, Solana e Binance Academy.
O radar pesquisa **as fontes configuradas**, não toda a internet. Adicione novos
protocolos, testnets, campanhas de pontos, programas e exchanges conforme necessário.

Em cada execução verifica HTTPS, domínio exato, IP público, redirecionamentos,
HTTP, limite de conteúdo e estrutura RSS/Atom. HTML não é aceito como feed.
Datas inválidas ficam desconhecidas. Publicações antigas/futuras são filtradas
quando há data verificável. Artigos são consultados individualmente; menus e
slogans gerais da plataforma não justificam gratuidade de uma campanha.

BitDegree: cards individuais de missões, cursos/quizzes e distribuição pública,
status, requisitos e recompensas. Abas de prêmios não duplicam a missão. Status
encerrado/pausado e data passada prevalecem sobre “Join now”. Campanhas de casino
e apostas não são incluídas. Não há login, CAPTCHA ou sessão. Conteúdo disponível
só após login/JavaScript pode não ser acessível; isso é limitação de cobertura.

Agregadores devem usar `official: false` e permanecem não confirmados. Para
confirmar, cadastre a página original do projeto como fonte `page` após validar
seu domínio. Não há promoção automática de agregadores a fontes oficiais.
Detalhes de cadastro em [`config/README.md`](config/README.md).

## Execução local e testes

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
ruff check .
python -m compileall -q src scripts main.py
python scripts/check_secrets.py
python -m src.main --dry-run
```

`--dry-run` não exige credenciais, não envia Telegram e não altera histórico.
Leia `reports/run.json` e `reports/summary.txt`. Para envio real, forneça as duas
variáveis de ambiente por mecanismo seguro e execute `python -m src.main`.
`python main.py` permanece como entrada compatível.

Saídas: `0` sem erros detectados; `2` cobertura/entrega parcial; `1` falha fatal.
Um job vermelho pode já ter entregue alertas: entregas confirmadas são preservadas
antes de terminar o workflow. Os testes bloqueiam rede e não enviam Telegram real.

## Assistente de estudo de quizzes

```bash
python -m src.quiz_analyzer config/quiz.example.json --output reports/quiz-results.json
```

Primeiro ajuste o JSON com perguntas/alternativas de materiais públicos autorizados,
URLs oficiais e domínios cadastrados conforme `config/README.md`. O exemplo é modelo
de entrada, não respostas reais coletadas de uma avaliação.

O analisador consulta as URLs fornecidas, compara termos e retorna alternativa
provável, raciocínio, confiança e trechos com citações, guardando o JSON para consulta.
É ferramenta lexical de estudo, sem IA paga: abstém quando a evidência é fraca ou
a pergunta é negativa. Não promete compreensão semântica nem dá confiança alta
a um casamento de palavras. **Não existe código de submissão automática**.

Também aceita `question_pages`: lista de objetos com `url`, `container_selector`,
`question_selector` e `option_selector` para ler perguntas de HTML público autorizado.
Por padrão extrai `fieldset`, `legend` e `label`. Isso não preenche nem envia formulários.

## Segurança e histórico

- Timeout, até três tentativas GET e backoff exponencial para falhas transitórias.
- XML sem entidades, domínio validado também nos redirecionamentos, limite de 2 MB,
  rejeição de destinos privados/locais e deduplicação por URL normalizada.
- Telegram em texto simples, sem HTML externo, divisão por unidades UTF-16,
  tratamento de `ok: false`, erros HTTP e 429. Credenciais são ocultadas dos logs.
- POST com timeout é entrega incerta e não é repetido imediatamente. Telegram e
  Git não têm transação conjunta: uma interrupção após aceitação da mensagem e
  antes de gravar estado pode causar repetição na próxima execução.
- Branch `radar-state`: apenas URLs, hashes das características dos alertas e
  datas dos resumos. Como o repositório é público, o histórico também será público.
  Não grava ID do chat, token, cookies, senha ou conteúdo de carteiras.
- Execução serializada. Falha de restauração/estado inválido interrompe sem apagar
  a deduplicação. Entrega falha não é marcada como enviada.

Não solicita chave privada/frase-semente. Não conecta carteiras, assina transações,
compra, deposita, transfere, faz staking ou envia respostas. Usa bibliotecas abertas,
páginas públicas, Actions e Telegram; não possui serviço com cobrança obrigatória.
Limites e políticas das plataformas se aplicam. Nenhum ganho ou quantidade diária
de oportunidades é garantido. As regras são heurísticas conservadoras: textos
ambíguos ou mudanças de layout precisam de revisão, não de suposições otimistas.

## Migração dos arquivos originais

- Removido `.github/workflows/blank.yml`: template que só imprimia exemplos.
- Removido `.github/workflows/main.yml`: vazio; tinha execução inválida no histórico.
- Removido `radar.yml` da raiz: não era reconhecido como workflow. Horário, Python,
  nomes dos Secrets e logs foram incorporados em `.github/workflows/radar.yml`.
- Preservado `radar-cripto-bot-inicial.zip` sem alteração como referência histórica;
  foi inspecionado, não é executado ou instalado automaticamente.
- README reescrito; adicionados código em `src/`, entrada compatível, fontes,
  dependências, testes, scripts de persistência/segredos e `.gitignore`.

Resultados e limitações da validação em [`VALIDATION.md`](VALIDATION.md).
