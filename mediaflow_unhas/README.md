# MediaFlow Unhas (GitHub Actions)

Módulo **independente** do Radar Cripto. Gera vídeos de 10 segundos com **10 fotos distintas** baixadas do Wikimedia Commons, organizadas em MP4 vertical 720x1280 com FFmpeg. Há 30 temas de unhas e três efeitos (zoom, fade e cortes).

Execute manualmente em **Actions > MediaFlow Unhas > Run workflow**. Se houver ao menos 10 imagens relevantes no Commons, os arquivos são disponibilizados nos artifacts. Marque **enviar_telegram** para mandar ao chat já configurado com TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID. Não alteramos os workflows do Radar.

A fonte Commons nem sempre contém 10 imagens por tema. Nesses casos a execução falha, em vez de repetir fotos. Confira credits.json e licenças antes de usar comercialmente. Geração por IA (ComfyUI) e bot de comandos em tempo real estão no pacote local MediaFlow v0.4; GitHub Actions não executa o ComfyUI sem GPU. Este módulo não publica TikToks.
