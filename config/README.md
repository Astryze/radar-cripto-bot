# Fontes e materiais

`sources.json` é uma lista de domínios exatos aprovados manualmente. Não use curingas.
Um domínio incluído como `official: true` é uma decisão editorial: valide sua autoria
antes de incluir. O programa verifica domínio, HTTPS, status HTTP e formato em cada
execução; não decide sozinho quem é dono de um domínio.

Tipos:
- `feed`: RSS 2.0/Atom validado como XML seguro; rejeita HTML e entidades externas.
- `listing`: links extraídos por `selector` e limitados por `path_pattern`.
- `bitdegree`: cards individuais de missões e distribuição pública com status.
- `page`: uma campanha individual ou página pública de regras, com título obrigatório.
- `json`: API pública com `items_path` e `item_fields` explícitos; não descobre endpoints por tentativa.

Na versão 2, `discovered_from` registra a página oficial usada para localizar cada
fonte. `min_interval_seconds` controla o intervalo por domínio (padrão 0,5 s).
`policy_urls` lista políticas oficiais que podem ser consultadas como evidência com
escopo restrito. A regra universal da FAQ BitDegree não comprova prêmio ou saque e
não remove uma obrigação financeira específica da missão.

`trusted_guilds` é usado no catálogo BitDegree com `official: false`: apenas as
guilds verificadas explicitamente podem receber confirmação. Não marque todo o
catálogo de missões criadas por usuários como fonte oficial.

Auditoria: `python -m scripts.audit_sources` gera `reports/source-audit.json`.
`config/source_audit.json` guarda uma fotografia real de desenvolvimento; a coleta
diária produz `reports/source-health.json` e mantém as datas/cooldowns no estado
persistente. HTTP 202 é pendência; só acompanhar um endereço posterior quando
a resposta fornecer `Location`/`Link rel=monitor` e ele estiver nos domínios permitidos.

`max_items` limita trabalho por fonte (1–50); `max_age_days` limita publicações com
data conhecida (1–365). Sem data válida, a publicação fica com data desconhecida,
e nunca ganha prazo aberto apenas pela idade. Não confunda publicação e encerramento.

Agregadores podem ser adicionados com `official: false`. Nunca justificam gratuidade
ou recompensa confirmada. Para confirmação, cadastre a página original do projeto
como uma fonte `page` oficial; a revisão dos domínios é manual, não uma busca irrestrita.

O exemplo de quiz é um modelo de entrada, não respostas reais coletadas. Para usá-lo,
cadastre o domínio oficial do material em uma fonte `page` (pode ser `enabled: false`,
permitindo estudo sem acrescentar a página ao radar). O analisador só aceita materiais
dos domínios oficiais configurados. Troque perguntas/alternativas por material público
cuja consulta seja autorizada. Nunca forneça cookies, tokens de sessão ou senha.
