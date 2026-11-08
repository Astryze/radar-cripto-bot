"""Pesquisa limitada de regras públicas, com evidência por URL e escopo de campanha."""
import re
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from .models import Conclusion, Cost
from .opportunity_filter import cost_evidence, deadline_info, segments
from .utils import canonical_url, normalize, plain_text, validate_url

RELEVANT = r"rules?|terms?|conditions?|requirements?|rewards?|prize|eligibility|participat|faq|round|mission|quiz|regras|requisitos"
EDUCATION = r"\b(quiz|quizzes|read|watch|learn|answer|course|rounds|micro.tasks|leia|curso|responda)\b"
UNCERTAIN = r"\b(may|might|could|estimated|chance|raffle|lottery|lucky draw|not guaranteed|subject to|sorteio|pode|condicional)\b"


def public_links(html, base_url):
    from urllib.parse import urljoin
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("article") or soup.select_one("main") or soup
    links, seen = [], set()
    for a in root.select("a[href]"):
        if a.find_parent(["nav", "footer", "header", "aside"]):
            continue
        label = a.get_text(" ", strip=True)
        url = canonical_url(urljoin(base_url, a.get("href", "")))
        if url in seen or not re.search(RELEVANT, normalize(label)):
            continue
        seen.add(url)
        links.append({"url": url, "label": label[:200]})
    return links


def investigate(candidate, client, official_domains, max_pages=3):
    if not candidate.verified:
        return candidate
    docs = [{"url": candidate.url, "text": candidate.text, "scope": "campaign", "official": True}]
    used = {canonical_url(candidate.url)}
    title_words = set(re.findall(r"[a-z0-9]{4,}", normalize(candidate.title)))
    for link in candidate.links:
        if len(docs) - 1 >= max_pages:
            break
        url = link["url"]
        if url in used:
            continue
        # Não seguir termos gerais da plataforma como se fossem regras desta missão.
        if not (url.startswith(candidate.url.rstrip("/") + "/") or
                len(title_words & set(re.findall(r"[a-z0-9]{4,}", normalize(url + " " + link["label"])))) >= 2):
            continue
        if urlsplit(url).hostname == "www.bitdegree.org" and urlsplit(url).path.startswith("/guilds/"):
            source_guild = urlsplit(candidate.url).path.split("/")[2:3]
            target_guild = urlsplit(url).path.split("/")[2:3]
            if source_guild != target_guild:
                continue
        try:
            validate_url(url, official_domains, resolve=False)
        except ValueError:
            continue
        used.add(url)
        try:
            body, final, kind = client.get(url, official_domains)
            if "html" not in kind.lower():
                continue
            text = plain_text(body, article_only=True)
            if len(text) >= 80:
                docs.append({"url": final, "text": text, "scope": "campaign", "official": True})
        except Exception as exc:
            candidate.investigation_errors.append(type(exc).__name__)
    # Políticas configuradas têm escopo explícito: não são evidência universal de prêmio.
    for url in candidate.source.policy_urls:
        try:
            validate_url(url, candidate.source.domains, resolve=False)
            body, final, kind = client.get(url, candidate.source.domains)
            if "html" in kind.lower():
                docs.append({"url": final, "text": plain_text(body, article_only=True),
                             "scope": "platform_policy", "official": True})
        except Exception as exc:
            candidate.investigation_errors.append(type(exc).__name__)
    candidate.documents = docs
    return candidate


def _bitdegree_policy(candidate):
    """FAQ universal de missões aplica-se só à participação educacional pública."""
    if (urlsplit(candidate.url).hostname != "www.bitdegree.org"
            or not re.fullmatch(r"/guilds/[^/]+/[^/]+", urlsplit(candidate.url).path.rstrip("/"))
            or not re.search(EDUCATION, normalize(candidate.text))
            or not re.search(r"\b(bits|mission|rounds)\b", normalize(candidate.text))):
        return None
    for doc in candidate.documents:
        if (doc.get("scope") == "platform_policy" and doc.get("official")
                and canonical_url(doc["url"]) == "https://www.bitdegree.org/faq"):
            match = re.search(r"All BitDegree Missions are free of charge\.?", doc["text"], re.I)
            if match:
                return {"url": doc["url"], "quote": match.group(),
                        "scope": "somente missões educacionais BitDegree; não comprova prêmio ou saque"}
    return None


def enrich(op, candidate, now):
    """Regras da campanha têm precedência sobre generalidades e rotas alternativas."""
    docs = candidate.documents or [{"url": candidate.url, "text": candidate.text,
                                    "scope": "campaign", "official": candidate.verified}]
    campaign_docs = [d for d in docs if d.get("scope") == "campaign" and d.get("official")]
    combined = "\n".join(d["text"] for d in campaign_docs)
    op.source_id = candidate.source.id
    guild = re.search(r"\nGuild\n([^\n]+)", candidate.text)
    if guild and urlsplit(candidate.url).hostname == "www.bitdegree.org":
        op.project = guild.group(1)[:150]
    op.investigated_urls = list(dict.fromkeys(d["url"] for d in docs))
    op.investigation_status = "parcial" if candidate.investigation_errors else "concluída com material público"
    if not candidate.verified:
        op.investigation_status = "sem confirmação oficial"
    cost, evidence = cost_evidence(combined, candidate.verified)
    op.cost = cost
    op.evidence.update(evidence)
    op.evidence["documentos"] = [f'{d["url"]} — {d["scope"]}' for d in docs]
    # Uma rota alternativa só é válida se for explicitamente completa e suficiente.
    # Nunca remover uma obrigação global "all participants must ...".
    for doc in campaign_docs:
        blocks = [p.strip() for p in re.split(r"\n\s*\n", doc["text"]) if p.strip()]
        for block in blocks:
            s = normalize(block)
            alternative = re.search(r"(?:alternative free (?:entry|route|participation)|free entry (?:route|method)|rota gratuita alternativa)", s)
            complete = re.search(r"(?:no (?:purchase or deposit|deposit or purchase) (?:is )?required|sufficient to (?:enter|participate)|no other (?:tasks|requirements)|sem compra ou deposito)", s)
            global_paid = any(re.search(r"(?:all participants|every participant|todos os participantes).{0,80}(?:must|required|obrigator)", normalize(sentence))
                              and cost_evidence(sentence, True)[0] == Cost.REQUIRED
                              for d in campaign_docs for sentence in segments(d["text"]))
            alt_cost, _ = cost_evidence(block, True)
            if alternative and complete and alt_cost == Cost.FREE and not global_paid:
                op.cost = Cost.FREE
                op.participation_route = block[:700]
                op.evidence["rota_gratuita"] = [doc["url"], block[:700]]
    policy = _bitdegree_policy(candidate)
    if policy and op.cost == Cost.POSSIBLE and not evidence.get("custo"):
        # Só retirar ambiguidades de descrições comerciais quando as tarefas
        # educacionais são expressamente identificadas e sem ação on-chain.
        tasks = candidate.text.split("Rounds", 1)[-1] if "Rounds" in candidate.text else candidate.text
        task_cost, task_evidence = cost_evidence(tasks, True)
        if task_cost != Cost.REQUIRED and not task_evidence.get("custos_ambiguos") and not task_evidence.get("taxa_rede"):
            op.cost = Cost.FREE
            op.evidence["gratuidade"] = [policy["quote"]]
            op.evidence["politica_oficial"] = [policy["url"], policy["scope"]]
            op.participation_route = "Somente os rounds educacionais públicos da missão para acumular Bits; sem operações financeiras."
    # Testnet explicitamente sem valor real + faucet gratuito + ausência de custo.
    normalized = normalize(combined)
    if (op.cost == Cost.POSSIBLE and re.search(r"test(?:net)? tokens (?:have|with) no (?:real |monetary )?value", normalized)
            and re.search(r"free faucet", normalized) and re.search(r"no (?:real funds|purchase or deposit) (?:are |is )?required", normalized)
            and not evidence.get("custo") and not re.search(r"mainnet (?:bridge|deposit|transaction)", normalized)):
        op.cost = Cost.FREE
        op.evidence["gratuidade"] = [s[:400] for s in segments(combined) if re.search(r"no .*required|free faucet", normalize(s))]
        op.participation_route = "Testnet com tokens sem valor e faucet gratuito, conforme regras oficiais; nenhum fundo real."
    if combined:
        op.deadline, op.deadline_at, paused = deadline_info(combined + "\n" + candidate.listing_text, candidate.listing_status, now)
        if paused:
            op.evidence["pausa"] = ["Campanha pausada na fonte oficial"]
    _rewards(op, combined if candidate.verified else "")
    _requirements(op, combined)
    if candidate.investigation_errors and op.cost in {Cost.FREE, Cost.GAS}:
        op.cost = Cost.POSSIBLE
        op.evidence["investigacao_incompleta"] = ["Regras relacionadas não puderam ser verificadas; não anunciar custo zero."]
    op.conclusion = conclusion(op)
    return op


def _rewards(op, text):
    lines = segments(text)
    reward_lines = [s for s in lines if re.search(r"\b(earn|collect|receive|reward|rewards|win|prize|ganhe|receba|recompensa)\b", normalize(s))]
    assets = []
    for line in reward_lines:
        for quantity, asset in re.findall(r"\b(\d[\d,.]*)\s+\$?([A-Z][A-Z0-9]{1,11}|Bits|bits|points|credits|NFTs?)\b", line):
            label = asset.upper()
            kind = "pontos internos" if label in {"BITS", "POINTS", "XP", "DEGREE"} else "créditos" if label == "CREDITS" else "valor nominal em moeda" if label in {"USD", "EUR", "BRL"} else "NFT" if label.startswith("NFT") else "token"
            pool = bool(re.search(r"\b(pool|total|shared|share|prize pool)\b", normalize(line)))
            assets.append({"asset": asset, "quantity_announced": quantity, "kind": kind,
                           "allocation": "pool total; não valor individual" if pool else "escopo individual não confirmado",
                           "quote": line[:350]})
    op.reward_assets = assets[:12]
    token_assets = [a for a in assets if a["kind"] == "token"]
    if token_assets:
        op.token = ", ".join(dict.fromkeys(a["asset"].upper() for a in token_assets))
        op.token_quantity = "; ".join(a["quantity_announced"] + " " + a["asset"] + " (" + a["allocation"] + ")" for a in token_assets)
    elif match := re.search(r"(?:Token|Reward token|Asset)\s*:\s*\$?([A-Z][A-Z0-9]{1,11})\b", text):
        op.token = match.group(1)
    # Não obter preços nem presumir que um ticker significa listagem/saque.
    values = [s for s in reward_lines if re.search(r"(?:worth|valued at|valor (?:de|estimado))\s*[$€R]", s, re.I)]
    if values:
        op.estimated_value = values[0][:300] + " — valor anunciado, não cotação independente"
    if re.search(r"\b(?:bits|degree|points|xp)\b", normalize(" ".join(reward_lines))):
        op.reward_type = "pontos internos; não equivalem a token negociável ou dinheiro sacável"
        if token_assets:
            op.reward_type = "mista: pontos internos e possível prêmio em tokens (ver alocação)"
    if re.search(UNCERTAIN, normalize(" ".join(reward_lines))):
        op.reward_status = "estimada"
    if re.search(r"(?:rewards?|tokens?) (?:are |can be )?(?:withdrawable|withdrawn|tradable)|(?:can withdraw|can trade) (?:your |the )?(?:rewards|tokens)", normalize(text)):
        op.withdrawability = "possibilidade de saque/negociação declarada pela fonte; requisitos pessoais não verificados"
    if re.search(r"(?:bits|points).{0,50}(?:not tradable|cannot be withdrawn|not withdrawable|in.game points)", normalize(text)):
        op.withdrawability = "pontos internos sem saque/negociação comprovados"
    for line in lines:
        if re.search(r"\b(start date|starts on|begins on|inicio)\b", normalize(line)):
            from .opportunity_filter import DATE
            from .utils import parse_date
            match = re.search(DATE, line, re.I)
            date = parse_date(match.group()) if match else None
            if date:
                op.starts_at = date.isoformat()
                break


def _requirements(op, text):
    s = normalize(text)
    if re.search(r"\bkyc\b|identity verification|verificacao de identidade", s):
        required = re.search(r"kyc (?:is )?(?:required|mandatory)|(?:must|need to) (?:pass|complete) kyc|identity verification is required", s)
        optional = re.search(r"no kyc|kyc (?:is )?(?:optional|not required)", s)
        op.kyc = "obrigatório (identificação e privacidade)" if required else "dispensado ou opcional conforme texto" if optional else "mencionado; verificar regras"
    excluded = re.search(r"(?:brazil|brasil)(?: residents)? (?:is |are )?(?:not eligible|excluded|ineligible|not supported)|(?:except|excluding|not available in|restricted countries:|excluded countries:).{0,100}\b(?:brazil|brasil)\b", s)
    included = re.search(r"(?:brazil|brasil) (?:is |are )?(?:eligible|supported|included)|(?:available|open) (?:to users )?in (?:brazil|brasil)", s)
    if excluded:
        op.eligibility = "Brasil não elegível"
    elif included:
        op.eligibility = "Brasil confirmado"
    op.countries = [line[:300] for line in segments(text) if re.search(r"eligible countries|restricted countries|excluded countries|paises elegiveis|brazil|brasil", normalize(line))][:6]
    op.eligibility_requirements = [line[:300] for line in segments(text) if re.search(
        r"new users? only|first.time|eligible users|verified (?:users|accounts)|account must|already claimed|only (?:new|existing) users|novos usuarios|contas verificadas", normalize(line))][:6]
    op.eligibility_basis = ("país explicitamente confirmado; requisitos pessoais ainda não verificados" if op.eligibility == "Brasil confirmado"
                            else "país explicitamente excluído" if op.eligibility == "Brasil não elegível" else "país e requisitos pessoais não confirmados")
    if op.eligibility_requirements:
        op.eligibility_basis += "; elegibilidade condicionada ao perfil da conta"


def conclusion(op):
    if op.deadline == "encerrado":
        return Conclusion.CLOSED
    if not op.official:
        return Conclusion.UNKNOWN
    if op.cost == Cost.REQUIRED:
        return Conclusion.REQUIRED
    if op.cost == Cost.GAS:
        return Conclusion.GAS
    if op.cost == Cost.FREE:
        if "obrigatório" in op.kyc:
            return Conclusion.KYC
        if op.reward_status != "confirmada" or "pontos internos" in op.reward_type:
            return Conclusion.UNCERTAIN
        return Conclusion.FREE
    return Conclusion.POSSIBLE if op.cost == Cost.POSSIBLE else Conclusion.UNKNOWN
