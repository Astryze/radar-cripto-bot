# MediaFlow Unhas: referências → IA → 10 novas imagens → vídeo → Telegram

## Limitação técnica
GitHub Actions padrão **não tem ComfyUI instalado com modelos ou GPU**. Neste
repositório o GitHub Actions roda validação do código. Para gerar as imagens é
necessário rodar ComfyUI na própria máquina, com um modelo SD1.5 compatível
e os nodes do workflow. Não há fallback para publicar as imagens originais.

## Instalação
- Instalar Python, ffmpeg, ComfyUI e modelo com licença adequada.
- ComfyUI deve estar aberto em http://127.0.0.1:8188
- Instalar as dependências no ambiente Python:
  python -m pip install -r mediaflow_unhas/requirements.txt
  python -m pip install torch gallery-dl yt-dlp
- Copiar mediaflow_unhas/workflow_img2img_example.json e substituir o texto
  REPLACE_WITH_INSTALLED_SD15_CHECKPOINT.safetensors por um checkpoint que
  esteja instalado em ComfyUI/models/checkpoints.
- O JSON no formato API precisa dos três marcadores literais:
  {{PROMPT}} em CLIPTextEncode, {{SEED}} em KSampler e
  {{REFERENCE_IMAGE}} em LoadImage. Exemplo usa img2img padrão.
- Opcionalmente adaptar para IPAdapter ou ControlNet, se estiverem instalados.

## Rodar com referências próprias/autorizadas
python mediaflow_unhas/reference_transform.py \
    --tema vermelhas_elegantes \
    --referencia ./referencias/unhas01.jpg \
    --referencia ./referencias/unhas02.jpg \
    --workflow mediaflow_unhas/workflow_img2img_example.json \
    --saida output/unhas-ia \
    --enviar-telegram

O envio Telegram lê TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID do ambiente local.
Sem --enviar-telegram, não envia. Não exponha tokens.

## Coletar referências de plataformas públicas
Instale gallery-dl e yt-dlp. Links públicos HTTPS Pinterest, TikTok e Douyin
podem ser baixados **quando suportados pelos extratores**; podem falhar por
mudanças das plataformas e restrições. Não contorne login/proteções.

python mediaflow_unhas/reference_transform.py \
    --tema vermelhas_elegantes \
    --referencia "https://www.pinterest.com/pin/SEU_PIN/" \
    --allow-public-references \
    --workflow mediaflow_unhas/workflow_img2img_example.json \
    --saida output/unhas-ia

Fotos de referência ficam separadas em references/ e nunca entram como quadros
do vídeo final. Toda imagem final é produzida pelo ComfyUI, avaliada por CLIP e
verificação de duplicidade; apenas as dez saídas aprovadas vão para generated/,
então final.mp4 (10 imagens, 10 s, 9:16), com relatório JSON e envio opcional.
A filtragem pode falhar: revisar as mãos/unhas antes de publicar.

**Direitos autorais:** uma imagem estar disponível para download não concede
permissão automática de adaptação/publicação. Use referências próprias ou
licenciadas/autorizadas, e respeite as condições de cada plataforma.

## CI
O workflow do GitHub agora roda testes, não gera vídeos a partir de fotografias
stock nem envia automaticamente prévias inadequadas ao Telegram.
