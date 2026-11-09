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


def opportunity_message(op, event="oportunidade verificada"):
    return "\n".join([
        f"RADAR CRIPTO — {event.upper()}",
        f"Campanha: {op.title}", f"Projeto: {op.project}",
        f"Recompensa: {op.reward}", f"Natureza: {op.reward_type}",
        f"Token: {op.token}", f"Quantidade: {op.token_quantity}",
        f"Valor: {op.estimated_value}", f"Saque/negociação: {op.withdrawability}",
        f"Custo: {op.investment_classification} ({op.cost})", f"Conclusão: {op.conclusion}",
        f"Esforço: {op.effort}; prioridade {op.priority} ({op.score}/100)",
        f"Confiança da análise: {op.confidence}",
        f"Brasil: {op.eligibility}", f"Elegibilidade: {op.eligibility_basis}", f"KYC: {op.kyc}",
        "Restrições da conta: " + (" | ".join(op.eligibility_requirements) or "não informadas"),
        f"Prazo: {op.deadline}" + (f" — {op.deadline_at}" if op.deadline_at else " — data não informada"),
        f"Início: {op.starts_at or 'não informado'}",
        f"Confirmação oficial: {'sim' if op.official else 'não'}; investigação {op.investigation_status}",
        f"Rota de participação: {op.participation_route}",
        "O que fazer:", *[f"• {step}" for step in op.steps],
        "Evidência de custo zero: " + " | ".join(op.evidence.get("gratuidade", [])),
        "Fontes das regras: " + " | ".join(op.investigated_urls),
        f"Link para participar: {op.url}",
        "Pontos e sorteios não garantem tokens ou renda. Confira as regras antes de participar.",
    ])


def daily_summary(opportunities, errors, day, source_count, new_count=None, unavailable=None, pending_count=0, highlight_urls=None):
    from collections import Counter
    from .models import Cost
    from .scoring import actionable
    counts = Counter(o.cost for o in opportunities if o.deadline != "encerrado")
    best = sorted([o for o in opportunities if actionable(o) and (highlight_urls is None or o.url in highlight_urls)], key=lambda o: -o.score)[:5]
    lines = ["RADAR CRIPTO — RELATÓRIO DIÁRIO", f"Data: {day} (Brasília)",
             f"Novas campanhas encontradas: {len(opportunities) if new_count is None else new_count}",
             f"Campanhas analisadas: {len(opportunities)}",
             f"Gratuitas confirmadas: {counts[Cost.FREE]} (participação; não ganho garantido)",
             f"Gratuitas com taxa: {counts[Cost.GAS]}",
             f"Gratuitas com KYC: {sum(o.cost == Cost.FREE and 'obrigatório' in o.kyc and o.deadline != 'encerrado' for o in opportunities)}",
             f"Gratuitas com recompensa incerta/pontos: {sum(o.conclusion == 'GRATUITA, MAS COM RECOMPENSA INCERTA' for o in opportunities)}",
             f"Possíveis investimentos: {counts[Cost.POSSIBLE]}",
             f"Investimento obrigatório: {counts[Cost.REQUIRED]}",
             f"Campanhas encerradas: {sum(o.deadline == 'encerrado' for o in opportunities)}",
             f"Não confirmadas: {counts[Cost.UNKNOWN]}",
             f"Fontes consultadas: {source_count}",
             f"Fontes indisponíveis: {len(errors) if unavailable is None else unavailable}",
             f"Fontes aguardando resultado (202): {pending_count}",
             "", "Melhores novidades gratuitas abertas:"]
    if best:
        lines.extend(f"• {o.title} — {o.priority}; {o.conclusion}; Brasil: {o.eligibility}\n{o.url}" for o in best)
    else:
        lines.append("Nenhuma novidade com gratuidade comprovada e prazo aberto nesta coleta.")
    if errors:
        lines.append("Cobertura parcial — " + "; ".join(errors[:8]))
    lines.append("Pontos internos e sorteios não são dinheiro garantido. Detalhes novos/atualizados seguem em alertas separados.")
    return "\n".join(lines)
