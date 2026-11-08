# Radar 2.3 — integração autenticada interrompida pelos termos

Base: 5856e8d728d8945747e0cf60f73aaad1474d30ac.

## Impedimento encontrado antes da implementação do navegador

Fonte oficial: https://www.bitdegree.org/terms-of-service
Versão indicada na página: 1.6, atualizada em 05/03/2025; consultada em 08/11/2026.
Na seção 10, a plataforma declara proibida a cópia de conteúdo com tecnologia de
robôs/crawlers. A seção também restringe scripts que afetem a operação. Não foi
identificada autorização específica que permita coletar os quizzes autenticados para
análise e retransmissão automática. A solicitação desta versão manda interromper a
análise caso a plataforma proíba esse tipo de acesso; portanto a integração autenticada
foi interrompida antes de abrir Chromium, solicitar login ou processar uma sessão.

Não há alegação de que a plataforma detectou ou bloqueou esta implementação: ela não
foi executada. O impedimento é a regra publicada, não uma falha HTTP ou de Chromium.
A propriedade da conta pelo usuário não demonstra autorização da plataforma para
crawler. Uma autorização específica da BitDegree permitiria reavaliar o escopo e
implementar somente os acessos que ela autorizar. Não há flag para contornar a barreira.

## O que foi entregue

- `.auth/` no gitignore para proteção preventiva de arquivos locais de sessão.
- `src/bitdegree_access_policy.py`: barreira explícita com fonte, seção e motivo.
- `scripts/bitdegree_login.py`: entrada local que informa o impedimento e termina com
  código 2, sem navegador, sem solicitar senha e sem exportar estado. Não é um login
  funcional e não deve ser descrito como tal.
- `src/bitdegree_authenticated.py`: registra por missão que não houve tentativa de
  carregamento/autenticação. Contagens e HTTP são null, nunca zero perguntas alegadas
  a partir de uma coleta não executada. Saída 0 significa etapa ignorada por política.
- Workflow: registra esse bloqueio em relatório próprio e continua as demais etapas.
  Não recebe o Secret de sessão, não instala Chromium e não reconstrói credenciais.
- README e sete testes offline novos. Nenhuma funcionalidade 2.2 foi removida.

## Sessão e configuração

Não execute login para esta integração e não crie `BITDEGREE_STORAGE_STATE_B64` agora.
Não é necessário enviar estado de sessão a este repositório, ao assistente ou ao Telegram.
Não foi implementada a importação desse Secret nem um fluxo de renovação: não há sessão
consumida que possa expirar. Um eventual Secret já existente não é lido por esta etapa.
Não foram adicionadas dependências Playwright/Chromium sem uma execução autorizada.

## Validação

252 testes aprovados: os 245 existentes preservados e sete novos. Pytest bloqueia rede
nos testes e nenhuma conta real é usada. Novos testes cobrem bloqueio antes de criar
sessão, ausência de override, seis missões como não executadas, Secret ausente/presente
sem leitura ou exposição, gitignore e workflow sem transmissão de sessão.

Executados pytest, Ruff, compileall, validação YAML, actionlint e scanner de credenciais.
A execução real do módulo de bloqueio gerou `reports/bitdegree-authenticated.json` com
as seis missões e status `not_attempted_policy_block`. Nenhuma análise autenticada real,
login, extração dinâmica, iframe ou entrega de resposta foi testada ou alegada.

## Resultado das seis missões nesta versão

Ledger Atom; Vega Bet; Lucky Rollers; BC.GAME; Winna; Stake: todas não consultadas com
sessão autenticada, por política. Quantidade de perguntas autenticadas: não determinada.
Os resultados públicos reais da versão 2.2 permanecem em docs/bitdegree-v22-diagnostic.json;
eles não são reapresentados como execução autenticada 2.3. A versão solicitada de
Chromium autenticado não está concluída nem habilitada.
