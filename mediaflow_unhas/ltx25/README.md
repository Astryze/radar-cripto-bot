# MediaFlow Unhas — LTX 2.5 (prova de conceito)

**Status:** integração local preparada. **Uma geração LTX real somente ocorre com GPU CUDA e pesos oficiais instalados.** O script nunca substitui IA por slideshow fingindo que o pincel foi filmado.

## Fontes e licença

- Código/modelo oficial: https://github.com/Lightricks/LTX-2
- Alternativa para placas menores (não instalada pelo nosso runner): https://github.com/deepbeepmeep/WanGP
- Código LTX-2: Apache-2.0. **Pesos LTX-2.5: LTX-2.x Community License**, com condições próprias; avaliar antes de uso comercial.
- O download de componentes oficiais de exemplo ocupa aproximadamente **66 GiB no disco**; o uso de GPU e VRAM depende da configuração. GitHub Actions padrão sem CUDA não roda essa geração.

## Experimento 01: brilho magnético cat-eye esmeralda

Imagem de entrada: a foto original do conjunto esmeralda produzida no MediaFlow (não guardada no Git para evitar um binário enorme). Efeito: ímã se move sobre o esmalte verde e o brilho diagonal acompanha sua trajetória sem alterar o desenho das unhas. Resultado pretendido: **576 × 1024, 24 fps, 121 quadros (~5 s)**.

Este é um teste curto de movimento real por IA, **não um tutorial completo de 24 s**. Só ampliamos o fluxo depois de revisar se a unha e os dedos permanecem consistentes.

## Executar em GPU NVIDIA local

1. Instale uma versão de Python compatível, uv e drivers CUDA. Clone o LTX em third_party/LTX-2, seguindo a documentação oficial:

       git clone https://github.com/Lightricks/LTX-2.git third_party/LTX-2
       cd third_party/LTX-2
       uv sync --extra natten

2. Aceite os termos em https://huggingface.co/Lightricks/LTX-2.5 e baixe, mantendo a estrutura de subdiretórios dentro de third_party/LTX-2/models/ltx-2.5:

   - diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors
   - text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors
   - vae/ltx-2.5-video-vae-bf16.safetensors
   - vae/ltx-2.5-audio-vae-bf16.safetensors
   - latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors

3. Volte à raiz do projeto e instale Pillow. Faça primeiro o pré-teste, que só cria um plano JSON (sem geração):

       python -m pip install Pillow
       python -m mediaflow_unhas.ltx25.runner --image /caminho/manicure_esmeralda.png --outdir output/ltx25

4. Para gerar com **o LTX real**:

       python -m mediaflow_unhas.ltx25.runner --image /caminho/manicure_esmeralda.png --outdir output/ltx25 --run

O runner chama o CLI oficial com a opção --image IMAGE 0 1.0 replace, verifica GPU e arquivos de pesos ANTES de executar e verifica dimensão/duração do MP4 com ffprobe depois. Sem GPU, o modo --run dá erro em vez de apresentar um vídeo simulado.

## Verificação sem GPU

       python -m pip install Pillow pytest
       python -m pytest mediaflow_unhas/ltx25/tests -q

O CI gratuito testa elaboração do comando oficial, geometria 9:16, imagem válida, falha segura por falta de GPU e **ausência de MP4 falso**.

## Limitações e direitos

Uma sequência de ações de manicure (gel, ímã, pincel, strass) pode falhar mesmo no modelo correto; é essencial revisar visualmente o primeiro clipe. Não configurar Telegram para envio automático de saídas não revisadas. Não usar fotos de terceiros sem verificar licença e direito de transformação.

Não há endpoint remoto pago, instalação silenciosa de ComfyUI ou GPU paga neste projeto. O envio ao Telegram só deverá ser ativado após passar na revisão visual humana.
