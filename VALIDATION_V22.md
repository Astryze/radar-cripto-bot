# BitDegree 2.2 — diagnóstico de extração, sem declarar resolução demonstrada

Base: 4b6ee404c277a5971cabaa03b4916c35e78df016. Os 233 testes existentes foram
executados antes da alteração e preservados sem edição. Não foram adicionadas dependências.

## Motivo observado na versão 2.1

As seis URLs foram recuperadas do artifact da execução 42531779530, não escolhidas por
suposição. O HTML real respondeu 200 text/html em todas. Ele contém uma seção
`missions-server-content`, descrição, guilda e uma lista de títulos de rodadas sem links
para os conteúdos. O mount da aplicação contém `dashboard-layout` vazio. Nenhuma das
seis respostas contém bloco application/json ou application/ld+json com perguntas.
Os scripts inline encontrados são inicialização de analytics e mapa de rotas, não dados
de quiz. Rotas internas desse mapa não foram consultadas. A presença de bundle JavaScript
é observada; o conteúdo que apareceria após renderização não foi verificado.

O extrator 2.1 buscava fieldset/legend/label e data-quiz-question. Nenhuma das seis
respostas continha essas estruturas de perguntas. Portanto, trocar seletores não revela
perguntas ausentes do payload. A falha do diagnóstico anterior foi informar um estado
indiferenciado, sem preservar os motivos por missão. Não há evidência para afirmar que
todas exigem login, nem que uma API pública de perguntas existe.

A tentativa de inspeção renderizada foi recusada pela revisão automática por limite de
uso do navegador, não por rejeição da BitDegree. Nenhuma alternativa de renderização ou
contorno foi executada. O diagnóstico HTML já autorizado continuou sem executar JS.

## Evidência real

Ver docs/bitdegree-v22-diagnostic.json: resultado individual com URL, HTTP, content-type,
contagens, nomes públicos de rodadas, timestamp e hash do documento. Nenhum cookie,
token CSRF, HTML bruto, senha ou dado de conta é armazenado nesse relatório.
A leitura local usou o proxy do ambiente. O script reproduzível de produção mantém
validação DNS e HTTPS pelo HttpClient normal. Não houve login nem submissão.

Foram encontradas **zero perguntas reais** e produzidas **zero respostas reais**.
A ausência no HTML não comprova ausência na aplicação nem requisito de autenticação.
Não há demonstração de extração de quiz real. Esta entrega conclui o diagnóstico do
HTML e melhorias seguras; a resolução ponta a ponta continua limitada pela ausência de
payload público verificado e pela impossibilidade de inspecionar a interface renderizada.

## Implementação e testes

Novos módulos: public_questions (formatos explícitos HTML/JSON público), quiz_diagnostics
(forma real do shell observado) e scripts.diagnose_bitdegree (auditoria reproduzível).
O analisador reconhece questões múltiplas/escritas, mas abstém da resposta nessas modalidades.
O fluxo registra contagens e falhas técnicas; mantém cache e a integração de airdrops.
O CLI não envia missões sem perguntas ao Telegram. A análise nunca usa alternativas ou
formulários como evidência de si mesmos. JSON de FAQ e dados marcados como restritos
não são quizzes públicos. Não é adicionada API dinâmica sem documentação/autorização.

245 testes aprovados: 233 existentes + 12 novos, todos offline com rede bloqueada.
Os novos exemplos são explicitamente artificiais e não alegados como perguntas reais.
Executados pytest, Ruff, compileall, actionlint, leitura YAML e scanner de credenciais.
Os testes anteriores continuam cobrindo HTTP, orçamento, cache, falhas de Telegram e estado.
Nenhuma entrega real de resposta nova foi possível ou alegada. Os alertas de perguntas
continuam validados offline; não foram enviados dados simulados ao Telegram.
