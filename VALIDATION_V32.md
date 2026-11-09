# Validação do Radar 3.2

- Base da implementação: `32b26a37312c98604ea5a8619411b3b29318218d`.
- 341 testes offline passaram com Python 3.12. Ruff, compileall, actionlint e
  scanner de credenciais do projeto passaram.
- Dry-run local das fontes: o ambiente não resolveu os hosts externos. Nenhuma
  resposta HTTP ou oportunidade foi obtida por essa execução. O dry-run
  multiplataforma registrou ausência de credenciais e escopos para Galxe e
  Zealy. Nenhum alerta foi enviado.
- Consulta oficial independente ao GitHub confirmou a existência do
  [SECURITY.md da Anza](https://github.com/anza-xyz/agave/blob/master/SECURITY.md)
  e a exigência de queimar SOL sem reembolso por submissão. É um programa
  condicional de segurança, com investimento obrigatório para submeter.
- Os [termos da Solana Foundation](https://solana.org/tos) restringem a coleta
  sistemática. O coletor legado permanece cadastrado e fica desativado. O
  fallback em HTTP 429 tem regressão offline, preserva a tentativa primária e
  usa domínio independente. Agave é consultado diretamente na configuração
  padrão.
- [GET de quests Zealy](https://docs.zealy.io/api-reference/quests/list-quests)
  requer perfil administrativo na comunidade e retorna o catálogo sem
  paginação documentada. Consultas autenticadas dependem dos escopos e da
  chave somente leitura do administrador. Respostas simuladas não são
  evidência de campanhas reais.
- Ethereum, Polygon, Arbitrum, Optimism, Base, Starknet e ZKsync mantêm a
  cobertura existente. Quizzes dependem de autorização por plataforma.
