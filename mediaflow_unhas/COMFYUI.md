# ComfyUI local — 10 fotos de unhas para vídeo de 10 segundos

Integração de **MediaFlow Unhas** com o [ComfyUI oficial](https://github.com/Comfy-Org/ComfyUI). Essa etapa é independente do Radar Cripto. Não utiliza API paga.

## Pré-requisitos

1. Instale o ComfyUI no computador e carregue um **checkpoint local licenciado para o seu uso**.
2. Abra um workflow simples `CheckpointLoaderSimple → CLIPTextEncode → KSampler → VAEDecode → SaveImage`.
3. No texto positivo do CLIPTextEncode, digite literalmente **`{{PROMPT}}`**.
4. No campo seed do sampler, opcionalmente use o marcador **`{{SEED}}`** no JSON exportado, para variar cada imagem. Caso não use, habilite uma estratégia de seed diferente a cada geração.
5. Na interface do ComfyUI, exporte o workflow **formato API** (não o JSON comum de interface) para `workflow_api.json`.
6. Inicie o ComfyUI em `http://127.0.0.1:8188` (não abra a API publicamente).

## Execução

Em computador que esteja executando o ComfyUI:

```bash
python -m pip install -r mediaflow_unhas/requirements.txt
python mediaflow_unhas/comfy_local.py \
  --tema vermelhas_elegantes \
  --workflow workflow_api.json \
  --server http://127.0.0.1:8188 \
  --efeito zoom \
  --saida output/unhas_ia
```

Resultado: 10 arquivos JPG distintos, um `final.mp4` vertical 720×1280 com duração de 10 segundos, e `manifest.json`. O script usa `POST /prompt`, `GET /history/{prompt_id}` e `GET /view`, conforme o exemplo de API oficial do ComfyUI. É necessário FFmpeg com libx264.

## Limitações

- **Não executa geração IA dentro do GitHub Actions gratuito**, porque os runners normais não disponibilizam a GPU/modelos locais necessários. O workflow GitHub Actions existente continua trabalhando com fotos da Wikimedia Commons.
- Para dar comandos pelo Telegram de forma contínua é preciso deixar o programa local em execução; o runner manual GitHub Actions não substitui um bot ativo.
- Modelos de imagem e imagens da internet têm condições de licença que precisam ser respeitadas.
- A saída da IA é uma fotografia sintética, não um registro de trabalho real de manicure.
- O script falha se encontrar imagens repetidas; não fabrica resultados nem envia vídeos incompletos.
