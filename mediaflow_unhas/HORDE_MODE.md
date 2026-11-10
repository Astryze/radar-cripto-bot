# MediaFlow Unhas v2 — AI Horde em vez de ComfyUI

A nova integração executa img2img remotamente pela API AI Horde. O GitHub
Actions pode chamar a API sem GPU e sem instalação do ComfyUI.

## Operação
- Chave anônima: AI_HORDE_API_KEY=0000000000 (padrão).
- Opcionalmente configurar uma chave pessoal AI Horde para melhorar prioridade.
- O modo anônimo é gratuito, mas lento e com resolução pequena, filas
  imprevisíveis e limites de uso. Não há garantia de 10 resultados premium.
- Referências são enviadas para terceiros voluntários; usar apenas material
  próprio, licenciado ou autorizado para processamento.
- Nunca inserir fotos de referência cruas no vídeo final.

## Dependências
Instalar Python, FFmpeg e, no terminal:
    python -m pip install -r mediaflow_unhas/requirements.txt
    python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    python -m pip install gallery-dl yt-dlp

## Gerar com referência local
    python mediaflow_unhas/horde_transform.py --tema vermelhas_elegantes --referencia ./referencias/unha01.jpg --saida output/unhas-horde

## Referência pública de Pinterest/Douyin/TikTok (com direitos de uso adequados)
    python mediaflow_unhas/horde_transform.py --tema pretas_brilho --referencia "https://www.pinterest.com/pin/SEU_PIN/" --allow-public-references

## Referências por Openverse (sem conta)
    python mediaflow_unhas/horde_transform.py --tema vermelhas_elegantes --auto-references

Envio ao Telegram é opcional com --enviar-telegram; exige variáveis de ambiente
TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID. O código nunca envia referências cruas.

## Garantias e limitações
- Só renderiza MP4 de 10 segundos após aceitar 10 saídas geradas.
- Analisa conteúdo com CLIP e duplicidade; revisão humana ainda necessária.
- Resolução anônima 512/576 px, ampliar para 720x1280 não aumenta qualidade real.
- O AI Horde pode recusar, bloquear ou demorar muito por depender de voluntários.
- Modificar fotos por IA não concede automaticamente direitos comerciais de uso.
- Workflow antigo baseado em ComfyUI fica como legado e não é obrigatório.


Teste de produção solicitado em 2026-11-10. O push com marcador executa um ciclo sem entrega automática ao Telegram.
