# Radar 3.1 — coleta parcial

O dry-run anterior, execução 42539069116, registrou dois HTTP 429 em
https://solana.com/news, seguidos de cooldown de 15 minutos. Nenhum timeout
foi registrado para essa listagem. Sem endpoint alternativo oficial confirmado,
o radar segue pelas outras fontes e respeita a espera da Solana.

https://polygon.technology/blog retornou HTTP 200 e 12 itens. A verificação
registrou um artigo acima de 2 MB. As 12 requisições de artigos tinham HTTP 200.
O artefato anterior não vincula a falha de tamanho a uma URL individual.
A versão 3.1 guarda essa associação e tenta uma leitura integral de até 4 MB
para artigos oficiais da Polygon. Acima do limite, a página continua inconclusiva.

A configuração HTTP usa timeout de conexão de 5 segundos e de leitura de
20 segundos. Tentativas transitórias usam backoff com jitter. HTTP 408, 429 e
5xx passam pelo tratamento de retry; Retry-After é respeitado e esperas acima
do limite local ficam adiadas. Interrupções durante a leitura também podem ser
repetidas. Os relatórios guardam código, etapa, URL e motivo sem headers.

338 testes locais aprovados, incluindo 333 anteriores e cinco casos de regressão.
Ruff, compileall, actionlint, YAML e scanner de credenciais aprovados.
O modo parcial no workflow gera aviso e conserva os erros de cada fonte.
Zealy ainda depende de chave somente leitura e comunidades autorizadas.
