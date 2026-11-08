"""Regras conservadoras com trechos rastreáveis, sem inferência de gratuidade por slogan."""
import re
from datetime import timedelta

from .models import Cost, Opportunity
from .utils import normalize, parse_date, utcnow

CAMPAIGN = r"\b(airdrop|learndrop|learn\s*(?:&|and)\s*earn|quest|mission|campaign|testnet|rewards? program|incentive program|token distribution|campanha|missao|distribuicao de tokens|recompensas)\b"
ACTION = r"\b(join|participate|complete|claim|enroll|register|answer|collect|earn|solve|eligible|inscreva|participe|complete|resgate|ganhe|receba|colete)\b"
BENEFIT = r"\b(token[s]?|airdrop|reward[s]?|points|bits|degree|prize|usdt|usdc|btc|eth|nfts?|credits|recompensa[s]?|pontos|premio[s]?)\b"
FINANCE = r"\b(deposit[s]?|purchase[s]?|buy|stake|staking|paid nft|mint|subscription|entry fee|registration fee|membership|paid plan|pay|payment|hold|own|minimum balance|trading volume|trade|liquidity|deposito|compra|comprar|assinatura|taxa de inscricao|pagar|pagamento|saldo minimo|negociar)\b"
MANDATORY = r"\b(required|mandatory|must|need to|minimum|at least|prerequisite|to qualify|to participate|obrigatori[oa]|necessari[oa]|deve|precisa|minimo)\b"
OPTIONAL = r"\b(optional|optionally|not required|not necessary|no need|not mandatory|opcional|nao obrigatorio|nao e necessario|nao exige)\b"
FREE = r"\b(no (?:purchase or deposit|deposit or purchase) (?:is )?(?:required|necessary)|(?:participation|entry) is (?:completely |entirely )?free|free to participate|participacao (?:e )?(?:totalmente )?gratuita|sem (?:compra ou deposito|deposito ou compra)(?: obrigatorios?)?)\b"
GAS = r"\b(gas (?:fees?|costs?)|network fees?|transaction fees?|taxas? de (?:rede|gas|transacao))\b"
ONCHAIN = r"\b(on.chain|mainnet|bridge|swap|mint|transaction|transacao|ponte)\b"
DATE = r"(?:\d{4}-\d{2}-\d{2}(?:T[0-9:+Z-]+)?|\d{1,2}/\d{1,2}/\d{4}|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})"
DATE = "(?:" + DATE + r"|\d{1,2}\s+de\s+(?:janeiro|fevereiro|março|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+de\s+\d{4})"


def segments(text):
    return [s.strip() for s in re.split(r"\n+|(?<=[.!?])\s+|;|\bbut\b|\bhowever\b|\bmas\b", text, flags=re.I) if s.strip()]


def is_opportunity(title, text):
    combined = normalize(title + "\n" + text)
    if re.search(r"\b(casino|sports betting|wagering|gambling|apostas)\b", combined):
        return False
    if not (re.search(CAMPAIGN, combined) and re.search(ACTION, combined) and re.search(BENEFIT, combined)):
        return False
    # Um artigo longo pode mencionar campanhas alheias, testnet e recompensas em
    # parágrafos desconectados. Exigir campanha no título/cabeçalho e ação ligada
    # ao benefício; não transformar notícias de infraestrutura em oportunidades.
    header = normalize(title + "\n" + text[:350])
    if not re.search(CAMPAIGN, header):
        return False
    linked = any(re.search(ACTION, normalize(s)) and re.search(BENEFIT, normalize(s))
                 and len(s) <= 600 for s in segments(text))
    if not linked:
        return False
    # Guias genéricos e notícias retrospectivas não são anúncios de participação.
    if re.search(r"\b(how to avoid|scam|price prediction|market recap|golpe)\b", normalize(title)):
        return False
    if re.search(r"\b(what is|o que e)\b", normalize(title)) and not re.search(r"learn\s*(?:&|and)\s*earn", normalize(text[:350])):
        return False
    if re.search(r"\b(airdrop guide|guide to airdrops|history of|explained|how .*airdrop)\b", normalize(title)):
        return bool(re.search(r"\b(register now|join now|claim now|participate now)\b", combined))
    return True


def cost_evidence(text, official):
    evidence = {"custo": [], "gratuidade": [], "taxa_rede": [], "custos_ambiguos": []}
    for sentence in segments(text):
        s = normalize(sentence)
        financial = re.search(FINANCE, s)
        # A negação só vale para a cláusula; "no purchase required, deposit required"
        # é avaliado de novo por cláusulas separadas abaixo.
        clauses = re.split(r",|\band\b|\be\b", s)
        for clause in clauses:
            # Gas não é compra/depósito. Remover só a obrigação explícita de gas.
            clause = re.sub(r"(?:pay|payment of|pagar)\s+(?:the |a )?" + GAS, "", clause)
            if not re.search(FINANCE, clause):
                continue
            negated = bool(re.search(OPTIONAL, clause) or re.search(
                r"\b(no|without|sem|nao)\b.{0,45}" + FINANCE, clause))
            # Exigências diferentes na mesma frase anulam uma negação genérica.
            positive = re.search(r"\b(?:must|need to|required to)\s+(?:make a |make |have a )?" + FINANCE, clause)
            imperative = re.search(r"^\s*(?:to participate[, :]*)?(?:deposit|buy|stake|purchase|trade|mint|deposite|compre)\s+(?:at least |a minimum of )?(?:\$?\d|a paid|tokens|an nft)", clause)
            if positive or imperative or (not negated and re.search(MANDATORY, clause)):
                evidence["custo"].append(sentence[:400])
            elif not negated:
                evidence["custos_ambiguos"].append(sentence[:400])
        if re.search(FREE, s):
            evidence["gratuidade"].append(sentence[:400])
        if re.search(GAS, s) and not re.search(r"\b(no |without |zero |sponsored|covered|gasless|sem |patrocinad)", s):
            evidence["taxa_rede"].append(sentence[:400])
        # Contradição: "free" junto a requisito on-chain sem explicação do gas.
        if re.search(ONCHAIN, s) and not re.search(GAS, normalize(text)) and not re.search(OPTIONAL, s) and not re.search(r"gasless|sponsored|covered|testnet tokens have no value|test tokens have no value", s):
            evidence["custos_ambiguos"].append(sentence[:400])
        payment_context = re.sub(r"(?:pay|payment of|pagar)\s+(?:the |a )?" + GAS, "", s)
        if financial and re.search(r"\b(pay|payment|pagar|pagamento)\b", payment_context) and not re.search(OPTIONAL, payment_context) and not re.search(r"\b(no|without|sem|nao)\b", payment_context):
            evidence["custo"].append(sentence[:400])
    if not official:
        cost = Cost.UNKNOWN
    elif evidence["custo"]:
        cost = Cost.REQUIRED
    elif evidence["taxa_rede"] and evidence["gratuidade"] and not evidence["custos_ambiguos"]:
        cost = Cost.GAS
    elif evidence["gratuidade"] and not evidence["custos_ambiguos"]:
        cost = Cost.FREE
    else:
        cost = Cost.POSSIBLE
    return cost, {k: list(dict.fromkeys(v)) for k, v in evidence.items() if v}


def deadline_info(text, listing_status, now):
    dates = []
    for match in re.finditer(r"(?:deadline|ends? (?:on|at)|end date|claim until|participate until|valid until|prazo|encerra(?:mento)?(?: em)?|termina em)\s*[:\-]?\s*(" + DATE + ")", text, re.I):
        value = match.group(1)
        # dd/mm/yyyy: padrão brasileiro. Dia sem horário vale até 23:59:59 UTC.
        if re.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}", value):
            from datetime import datetime, timezone
            try:
                dt = datetime.strptime(value, "%d/%m/%Y").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        else:
            dt = parse_date(value)
        if dt:
            if "T" not in value:
                dt += timedelta(hours=23, minutes=59, seconds=59)
            dates.append(dt)
    end = min(dates) if dates else None
    s = normalize(text)
    closed = listing_status == "encerrado" or bool(re.search(
        r"\b(?:campaign|mission|airdrop|quest|claim(?:ing)?|registration|participation|campanha|missao)\s+(?:(?:is|has|has been|was|esta|foi)\s+)?(?:ended|closed|expired|encerrad[ao])\b|\b(?:status:\s*ended|registration is closed)\b", s))
    paused = listing_status == "pausado" or bool(re.search(r"\b(on pause|currently paused|mission is paused|campaign is paused)\b", s))
    if closed or (end and end < now):
        return "encerrado", end.isoformat() if end else None, paused
    if paused:
        return "não confirmado", end.isoformat() if end else None, True
    if end or listing_status == "aberto" or re.search(r"\b(join now|claim now|register now|campaign is open|registration is open|status: active|inscricoes abertas)\b", s):
        return "aberto", end.isoformat() if end else None, False
    return "não confirmado", None, False


def classify(candidate, now=None):
    now = now or utcnow()
    if not is_opportunity(candidate.title, candidate.text):
        return None
    op = Opportunity(candidate.title, candidate.source.name, candidate.url,
                     official=candidate.verified, source_url=candidate.verification_url or candidate.source.url,
                     published=candidate.published)
    op.cost, op.evidence = cost_evidence(candidate.text, candidate.verified)
    op.confidence = "média" if op.official else "baixa"
    op.deadline, op.deadline_at, paused = deadline_info(candidate.text + "\n" + candidate.listing_text, candidate.listing_status, now)
    if paused:
        op.evidence["pausa"] = ["Campanha pausada na fonte; não anunciada como disponível."]
    text = normalize(candidate.text)
    if re.search(r"\b(?:brazil|brasil)(?: residents)?\s+(?:(?:is|are|esta|e)\s+)?(?:not eligible|excluded|ineligible|not supported|nao elegivel)|(?:excluding|except|not available in|restricted in|restricted countries:|excluded countries:|paises restritos:|exclui)\s+.{0,80}\b(?:brazil|brasil)\b", text):
        op.eligibility = "Brasil não elegível"
    elif re.search(r"\b(?:brazil|brasil)\s+(?:(?:is|are|esta|e)\s+)?(?:eligible|supported|included|elegivel)|(?:available|open) (?:to users )?in (?:brazil|brasil)\b", text):
        op.eligibility = "Brasil confirmado"
    if re.search(r"\bkyc\b|identity verification|verificacao de identidade", text):
        op.kyc = "mencionado; verificar regras"
        if re.search(r"(?:no kyc|kyc (?:is )?(?:not required|optional))", text):
            op.kyc = "dispensado ou opcional conforme texto"
        elif re.search(r"(?:kyc (?:is )?(?:required|mandatory)|must (?:complete|pass) kyc|identity verification is required)", text):
            op.kyc = "obrigatório (identificação e privacidade)"
    lines = segments(candidate.text)
    rewards = [s for s in lines if re.search(BENEFIT, normalize(s)) and
               re.search(r"\b(earn|receive|collect|win|reward|rewards|prize|ganhe|receba|colete|recompensa)\b", normalize(s))]
    if rewards and candidate.verified:
        op.reward = rewards[0][:350]
        op.evidence["recompensa"] = [s[:350] for s in rewards[:3]]
        uncertain = bool(re.search(r"\b(may|might|could|estimated|potential|lucky draw|raffle|chance|sorteio|pode|estimad[oa])\b", normalize(" ".join(rewards))))
        op.reward_status = "estimada" if uncertain else "confirmada"
        if re.search(r"\b(bits|points|pontos|degree)\b", normalize(" ".join(rewards))):
            op.reward_type = "pontos internos; não equivalem a token negociável ou dinheiro sacável"
            if re.search(r"\b(token|usdt|usdc|btc|eth|crypto rewards)\b", normalize(" ".join(rewards))):
                op.reward_type = "mista/ambígua; pontos internos separados de eventual prêmio cripto"
        elif re.search(r"\b(token|usdt|usdc|btc|eth|crypto)\b", normalize(" ".join(rewards))):
            op.reward_type = "prêmio cripto descrito pela fonte; valor e recebimento não garantidos"
        else:
            op.reward_type = "outra recompensa descrita pela fonte"
    op.steps = [s[:220] for s in lines if re.search(ACTION, normalize(s))][:5]
    simple = re.search(r"\b(quiz|quizzes|course|watch|answer|read|curso|assistir|responder)\b", text)
    op.effort = "baixo" if simple else "médio"
    if re.search(r"\b(run a node|validator|deploy|daily|weekly|multiple transactions|executar um no|diariamente)\b", text):
        op.effort = "alto"
    from .investigation import enrich
    return enrich(op, candidate, now)
