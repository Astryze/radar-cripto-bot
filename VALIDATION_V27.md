# Radar 2.7

## Diagnóstico de 8 de novembro de 2026

O cadastro contém zero IDs de Spaces Galxe e zero subdomínios Zealy.
O endpoint administrativo de metadados dos Secrets foi recusado pelo conector
GitHub. O diagnóstico seguro na `main` verifica disponibilidade no runner por
meio das variáveis de ambiente mapeadas pelo workflow e registra somente o estado.
Uma credencial indisponível no runner não identifica se ela está ausente,
restrita por política ou cadastrada em outro escopo.

Zero consultas reais Galxe e zero Zealy no dry-run local, pois ambos os escopos
estão vazios. Os testes usam respostas offline. A Galxe sinaliza paginação parcial
e preserva a distinção entre status HTTP e erro GraphQL. O Zealy requer chave
somente leitura autorizada para cada comunidade administrada.

Bitcoin Basics permanece GRATUIDADE_NAO_CONFIRMADA. A pesquisa oficial de
novembro localizou novamente a reposição de outubro. Vagas, acesso brasileiro,
ausência de investimento obrigatório e resgate atual seguem pendentes.
[Anúncio oficial de outubro](https://www.binance.com/en/square/post/372547852237367).

## Validação

310 testes locais, com os 307 anteriores preservados. Os novos cenários verificam
ausência de credencial e escopo, acesso negado via GraphQL com HTTP 200 e a
diferença entre catálogo vazio e consulta com resultados. Ruff, compileall, YAML,
actionlint e scanner de credenciais passaram. BitDegree segue bloqueada.

O critério de sucesso depende de configurar acesso autorizado a cada plataforma
e obter uma resposta real. As instruções e o teste de conexão estão no README.
