# MediaFlow: geração real de imagens por CPU no GitHub Actions

## Projetos avaliados
1. leejet/stable-diffusion.cpp (selecionado): motor de Stable Diffusion em C++
com suporte a imagem-para-imagem, CPU, GGUF, LCM e IPAdapter. Licença MIT.
https://github.com/leejet/stable-diffusion.cpp
2. rupeshs/fastsdcpu: CPU / OpenVINO, LCM e outros modelos rápidos; alternativa
promissora, mas o modo CLI e os requisitos variam conforme o modelo.
https://github.com/rupeshs/fastsdcpu
3. huggingface/diffusers com optimum-intel OpenVINO: outra opção CPU, mas
com dependências mais pesadas.
https://github.com/huggingface/diffusers

## Modelo de teste
Lykon/dreamshaper-8-lcm (checkpoint 2,13 GB), licença
CreativeML OpenRAIL-M. Verifique termos do modelo para cada uso.
https://huggingface.co/Lykon/dreamshaper-8-lcm

## O que foi integrado
- mediaflow_unhas/cpu_provider.py gera imagens por sd-cli usando -i e --strength.
- mediaflow_unhas/horde_transform.py aceita --provider cpu.
- mediaflow_unhas/cpu_smoke.py cria uma referência original ilustrada e
  produz uma imagem real transformada, sem Telegram.
- .github/workflows/mediaflow-cpu-smoke.yml compila o motor e baixa modelo
  com checksum SHA-256 antes de chamar a inferência.

## Uso local depois de compilar o binário
    export SD_CPP_BINARY=/caminho/stable-diffusion.cpp/build/bin/sd-cli
    export SD_CPP_MODEL=/caminho/DreamShaper8_LCM.safetensors

    python mediaflow_unhas/main.py --provider cpu --tema vermelhas_elegantes \
      --referencia ./referencias/unha_autorizada.jpg --saida output/unhas-cpu

O pipeline ainda exige dez imagens de unha visualmente aprovadas para liberar
final.mp4 e envio por Telegram. As imagens originais NUNCA entram no MP4.

## Limites
- Não é necessário ComfyUI, Pexels, AI Horde, HF_TOKEN ou GPU.
- Geração CPU exige baixar modelo, compilar o motor e usar RAM/CPU do runner.
- O modelo LCM é rápido (4 passos), mas pode criar mãos deformadas e artes
  de unhas pouco fiéis. Não prometer qualidade profissional sem inspeção.
- O modelo é baixado por HTTPS a partir do Hugging Face, sem usar a API de
  inferência. Isto é apenas hospedagem dos pesos do modelo.
- GitHub Actions público e privado têm limites de recursos diferentes; projetos
  privados podem consumir minutos faturáveis.
- A execução completa de dez imagens ainda exige resultado real positivo do
  teste de uma imagem e ajuste da coleta de referências.
