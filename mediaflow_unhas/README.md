# MediaFlow v2 — substituição do ComfyUI por AI Horde

**Gerador padrão:** AI Horde remoto. Não exige GPU local nem instalação
ComfyUI. Consulte [HORDE_MODE.md](HORDE_MODE.md).

Com referências próprias/autorizadas:
    python mediaflow_unhas/main.py --tema vermelhas_elegantes --referencia ./unhas.jpg --saida output/unhas

Busca de referências com licença aberta (sem chave):
    python mediaflow_unhas/main.py --tema vermelhas_elegantes --auto-references

O comando somente envia vídeo se você adicionar --enviar-telegram
e existirem 10 imagens geradas aprovadas. O modo anônimo gratuito tem filas
e resolução limitadas; a execução real precisa ser validada. O modo anterior
ComfyUI é legado e NÃO é necessário para o novo comando.

---

# MediaFlow Unhas (GitHub Actions)

Módulo **independente** do Radar Cripto. Gera vídeos de 10 segundos com **10 fotos distintas** baixadas do Wikimedia Commons, organizadas em MP4 vertical 720x1280 com FFmpeg. Há 30 temas de unhas e três efeitos (zoom, fade e cortes).

Execute manualmente em **Actions > MediaFlow Unhas > Run workflow**. Se houver ao menos 10 imagens relevantes no Commons, os arquivos são disponibilizados nos artifacts. Marque **enviar_telegram** para mandar ao chat já configurado com TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID. Não alteramos os workflows do Radar.

A fonte Commons nem sempre contém 10 imagens por tema. Nesses casos a execução falha, em vez de repetir fotos. Confira credits.json e licenças antes de usar comercialmente. Geração por IA (ComfyUI) e bot de comandos em tempo real estão no pacote local MediaFlow v0.4; GitHub Actions não executa o ComfyUI sem GPU. Este módulo não publica TikToks.

<!-- Execução solicitada em 2026-11-10; envio de prévia ao Telegram, se o workflow iniciar. -->

Execução de entrega: 10 fotos distintas encontradas na Wikimedia Commons; workflow habilitado para envio Telegram em execução manual ou commit sinalizado.

<!-- Execução de teste com filtro rígido e envio Telegram solicitada em 2026-11-10. -->


## Imagens de qualidade (v0.9)

O fluxo tenta **Pexels -> Wikimedia Commons -> ComfyUI local (opcional)**. Todas as fotografias são avaliadas pelo modelo visual CLIP e filtros de nitidez, resolução e duplicidade. **Se não conseguir dez imagens aprovadas, não gera vídeo e não envia ao Telegram.**

- Para ativar o Pexels no GitHub Actions, adicione o segredo **PEXELS_API_KEY** em *Settings -> Secrets and variables -> Actions -> New repository secret*. A API oferece acesso gratuito conforme suas condições. Sem essa chave, a execução registra que Pexels foi ignorado.
- O fluxo do GitHub público não hospeda uma instância ComfyUI. Para gerar imagens por IA, rode o programa em uma máquina local ou runner próprio com ComfyUI instalado e configure **COMFYUI_WORKFLOW** como caminho do workflow JSON exportado em formato API, contendo os marcadores `{{PROMPT}}` e `{{SEED}}`. O endereço **COMFYUI_SERVER** deve ser local (`http://127.0.0.1:8188`).
- O Telegram não recebe prévias de commits automáticos. Envio somente pelo acionamento manual do workflow com `enviar_telegram=true` ou execução local com `--enviar-telegram`.
- São preservados créditos/licenças nos arquivos `credits.json`; revisar direitos de uso e as imagens antes da publicação final.
- O modelo visual ajuda a eliminar fotos de objetos aleatórios, mas não garante sozinho beleza editorial nem correspondência perfeita de estilo.


## Fonte sem chave — Openverse (2026-11-10)

O MediaFlow agora consulta **Openverse** mesmo sem PEXELS_API_KEY. Ordem de prioridade: Pexels (quando houver chave), **Openverse sem chave**, Wikimedia Commons e ComfyUI local configurado. Openverse retorna candidatos de fontes CC; o pipeline aceita apenas licenças CC0, domínio público, CC BY e CC BY-SA com metadados e origem de atribuição, e rejeita links suspeitos/redirecionamentos. A licença deve ser conferida antes da publicação comercial; licenças CC BY e CC BY-SA têm obrigações de atribuição e podem exigir compartilhamento pela mesma licença para adaptações. Uma foto com palavras adequadas ainda precisa passar pelo filtro visual CLIP, nitidez e duplicidade.

O catálogo do Openverse não é uma galeria de nail art premium e nem toda imagem estará licenciada de forma adequada. Pinterest/Douyin são úteis para inspiração, mas baixar de lá por ferramentas como gallery-dl não autoriza republicação. Somente adicionar imagens próprias, autorizadas ou com licença verificável ao material de publicação. O pipeline continua recusando gerar/enviar se faltar uma das dez fotografias necessárias.
