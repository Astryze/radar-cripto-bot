import time

import requests

from .utils import FetchError


def split_message(message, limit=3900):
    """Conta unidades UTF-16, incluindo emojis; sem HTML vindo de páginas externas."""
    if not 2 <= limit <= 4096:
        raise ValueError("Limite inválido")
    chunks, current, size = [], [], 0
    for char in message:
        width = len(char.encode("utf-16-le")) // 2
        if size + width > limit:
            chunks.append("".join(current))
            current, size = [], 0
        current.append(char)
        size += width
    if current:
        chunks.append("".join(current))
    return chunks


class TelegramBot:
    def __init__(self, token, chat_id, session=None, sleep=time.sleep, attempts=3):
        # Secrets colados com newline/espaços não devem virar parte do endpoint.
        token = token.strip() if isinstance(token, str) else token
        chat_id = chat_id.strip() if isinstance(chat_id, str) else chat_id
        if not token or not chat_id:
            raise ValueError("Configure TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID nos GitHub Secrets")
        if any(c.isspace() for c in token) or any(c in token for c in "/?#"):
            raise ValueError("TELEGRAM_BOT_TOKEN deve conter somente o token, sem URL ou espaços internos")
        self._url = f"https://api.telegram.org/bot{token}/sendMessage"
        self._chat = chat_id
        self.session = session or requests.Session()
        self.sleep = sleep
        self.attempts = attempts

    def send(self, message):
        for chunk in split_message(message):
            self._send_chunk(chunk)
            self.sleep(1.1)

    def _send_chunk(self, message):
        for attempt in range(self.attempts):
            try:
                response = self.session.post(self._url, json={"chat_id": self._chat, "text": message,
                    "link_preview_options": {"is_disabled": True}}, timeout=(5, 20), allow_redirects=False)
            except requests.RequestException:
                # Timeout de POST é ambíguo: pode ter sido entregue. Não repetir imediatamente.
                raise FetchError("Telegram: transporte incerto; entrega não confirmada") from None
            try:
                data = response.json()
            except ValueError:
                data = {}
            status = response.status_code
            response.close()
            if status == 200 and data.get("ok") is True:
                return
            code = data.get("error_code", status)
            if code == 429 and attempt + 1 < self.attempts:
                delay = data.get("parameters", {}).get("retry_after", 2 ** attempt)
                try:
                    delay = float(delay)
                except (ValueError, TypeError):
                    delay = 2 ** attempt
                if delay > 60:
                    raise FetchError("Telegram: limite de frequência excede orçamento de espera")
                self.sleep(max(1, delay, 2 ** attempt))
                continue
            if status in {500, 502, 503, 504} and attempt + 1 < self.attempts:
                self.sleep(2 ** attempt)
                continue
            if status in {401, 404}:
                raise FetchError(f"Telegram: HTTP {status}; confira TELEGRAM_BOT_TOKEN no Secret (somente token do BotFather, sem URL/prefixo bot)")
            # Nunca registrar a descrição livre recebida da API: ela pode ecoar dados.
            descriptions = {
                "bad request: chat not found": "chat não encontrado; confira TELEGRAM_CHAT_ID e envie /start ao bot",
                "bad request: chat_id is empty": "TELEGRAM_CHAT_ID vazio",
                "bad request: message is too long": "mensagem excedeu o limite da API",
                "forbidden: bot was blocked by the user": "bot bloqueado pelo destinatário",
                "forbidden: bot can't initiate conversation with a user": "envie /start ao bot antes da execução",
            }
            detail = descriptions.get(str(data.get("description", "")).lower())
            if detail:
                raise FetchError(f"Telegram: HTTP {status}; {detail}")
            raise FetchError(f"Telegram: API recusou mensagem (HTTP {status}; código {code if isinstance(code, int) else 'inválido'})")
        raise FetchError("Telegram: tentativas esgotadas")


def opportunity_message(op):
    return "\n".join([
        "RADAR CRIPTO — oportunidade verificada",
        f"Nome da campanha: {op.title}", f"Projeto/fonte: {op.project}",
        f"Recompensa: {op.reward}", f"Natureza: {op.reward_type}",
        f"Recompensa ({op.reward_status}): descrição da fonte, sem garantia de pagamento individual",
        f"Custo de participação: {op.cost}", f"Esforço: {op.effort}",
        f"Prioridade: {op.priority} ({op.score}/100)",
        f"Elegibilidade no Brasil: {op.eligibility}", f"KYC: {op.kyc}",
        f"Prazo: {op.deadline}" + (f" — {op.deadline_at}" if op.deadline_at else " — data não informada"),
        f"Status da confirmação: fonte oficial; confiança {op.confidence}",
        "O que precisa ser feito:", *[f"• {s}" for s in op.steps],
        "Evidência de gratuidade: " + " | ".join(op.evidence.get("gratuidade", [])),
        f"Link oficial: {op.url}",
    ])


def daily_summary(opportunities, errors, day, source_count):
    from .models import Cost
    from .scoring import actionable
    from collections import Counter
    counts = Counter(op.cost for op in opportunities)
    best = sorted([o for o in opportunities if actionable(o)], key=lambda o: -o.score)[:5]
    lines = [f"RADAR CRIPTO — resumo de {day} (Brasília)",
             f"Campanhas candidatas verificadas/analisadas hoje: {len(opportunities)}",
             f"Gratuitas confirmadas (inclui encerradas, quando identificadas): {counts[Cost.FREE]}",
             f"Gratuitas com taxa de rede: {counts[Cost.GAS]}",
             f"Exigem investimento: {counts[Cost.REQUIRED]}",
             f"Podem exigir investimento: {counts[Cost.POSSIBLE]}",
             f"Não confirmadas: {counts[Cost.UNKNOWN]}",
             f"Fontes consultadas: {source_count}; falhas: {len(errors)}",
             "Melhores oportunidades abertas com gratuidade confirmada:"]
    if best:
        lines.extend(f"• {o.title} — {o.priority}; {o.reward_type}; Brasil: {o.eligibility}\n{o.url}" for o in best)
    else:
        lines.append("Nenhuma oportunidade aberta com gratuidade confirmada pelas regras consultadas.")
    unavailable = sum(o.deadline == "encerrado" or "pausa" in o.evidence for o in opportunities)
    lines.append(f"Encerradas/pausadas identificadas: {unavailable}")
    if errors:
        lines.append("Cobertura parcial — falhas: " + "; ".join(errors[:15]))
    lines.append("Pontos internos não são dinheiro sacável. Campanhas com custo obrigatório não geram alertas gratuitos.")
    return "\n".join(lines)
