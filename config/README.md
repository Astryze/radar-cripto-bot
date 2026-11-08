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
