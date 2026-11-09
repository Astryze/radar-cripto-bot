# Radar 2.9

Implementados GET de usuário por UUID, busca por identificador vinculado, convites
paginados, avaliações e POST de verificação de associação. A documentação descreve
GET /users como busca filtrada. O POST de associação exige permissão compatível
com POST e habilitação explícita. O catálogo usa exclusivamente GET.
[Usuários](https://docs.zealy.io/api-reference/users/user-lookup),
[associação](https://docs.zealy.io/api-reference/communities/community-member-check)
e [autenticação](https://docs.zealy.io/authentication).

O perfil opcional registra apenas associação, papel, banimento, XP, nível, ranking
e contagens de carteiras. A consulta de convites preserva a contagem por estado e
indica quando o limite de páginas impede uma contagem completa. As avaliações
retêm somente flags e estrelas. O transporte registra modelos de rotas e status,
sem UUIDs, parâmetros pessoais, headers ou corpos de erro.

O catálogo indica prazo quando uma condição de data obrigatória já impede
participação, e sinaliza o contador quando atinge a cota. Para as demais quests,
disponibilidade, gratuidade, acesso brasileiro e resgate exigem comprovação
adicional. O relatório conserva menções a custos e valores de XP distintos de
recompensas financeiras. A automação permanece restrita às consultas implementadas.

331 testes aprovados, incluindo os 318 anteriores. Os 13 casos novos cobrem
autenticação, usuário, busca filtrada, convites, avaliações, associação, respostas
inválidas, escopo, HTTP 401/403/404, Retry-After, falha de rede e integração do
perfil com o catálogo. As chamadas desses testes são simuladas. Ruff, compileall,
YAML, actionlint e scanner de credenciais passaram.

Dry-run local com zero chamadas Zealy. O ambiente não disponibilizou
ZEALY_API_KEY e o cadastro ativo não tem comunidades nem declaração somente
leitura. Primeira consulta real autenticada pendente. Zero oportunidades
gratuitas Zealy confirmadas.
