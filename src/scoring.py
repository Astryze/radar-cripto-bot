from .models import Cost


def score(op):
    value = {Cost.FREE: 45, Cost.GAS: 15, Cost.POSSIBLE: 0,
             Cost.REQUIRED: -100, Cost.UNKNOWN: -20}[op.cost]
    value += {"baixo": 15, "médio": 5, "alto": 0}[op.effort]
    value += 10 if op.official else 0
    value += {"confirmada": 10, "estimada": 3, "desconhecida": 0}[op.reward_status]
    value += 10 if op.deadline == "aberto" else 0
    value += 10 if op.eligibility == "Brasil confirmado" else 0
    if op.eligibility_requirements:
        value -= 10
    if op.starts_at:
        from .utils import parse_date, utcnow
        if parse_date(op.starts_at) and parse_date(op.starts_at) > utcnow():
            value = 0
    if op.deadline == "encerrado" or "pausa" in op.evidence or op.eligibility == "Brasil não elegível":
        value = 0
    op.score = max(0, min(100, value))
    op.priority = "baixa"
    if (op.cost == Cost.FREE and op.official and op.deadline == "aberto"
            and op.eligibility == "Brasil confirmado" and op.reward_status == "confirmada"
            and op.effort == "baixo" and op.score >= 85 and not op.eligibility_requirements
            and op.conclusion != "GRATUITA, MAS COM RECOMPENSA INCERTA"
            and op.investigation_status != "parcial"):
        op.priority = "alta"
        op.confidence = "alta"
    elif (op.cost in {Cost.FREE, Cost.GAS} and op.score >= 40
          and op.deadline != "encerrado" and "pausa" not in op.evidence
          and op.eligibility != "Brasil não elegível"):
        op.priority = "média"
    return op


def actionable(op):
    from .utils import parse_date, utcnow
    if op.starts_at and parse_date(op.starts_at) and parse_date(op.starts_at) > utcnow():
        return False
    return (op.cost == Cost.FREE and op.official and op.deadline == "aberto"
            and op.eligibility != "Brasil não elegível" and "pausa" not in op.evidence)



def verified_alert(op):
    return (actionable(op) and op.eligibility == "Brasil confirmado"
            and op.reward_status == "confirmada" and op.investigation_status == "concluída com material público"
            and bool(op.evidence.get("gratuidade")) and bool(op.evidence.get("resgate"))
            and bool(op.evidence.get("recompensa"))
            and any(asset.get("kind") == "token" for asset in op.reward_assets)
            and op.conclusion in {"GRATUITA CONFIRMADA", "GRATUITA COM REQUISITO DE KYC"}
            and op.withdrawability.startswith("possibilidade de saque/negociação declarada")
            and not op.eligibility_requirements)


def opportunity_classification(op, now=None):
    from .utils import parse_date, utcnow
    end = parse_date(op.deadline_at)
    if op.deadline == "encerrado" or (end and end <= (now or utcnow())):
        return "EXPIRED"
    if op.eligibility == "Brasil não elegível":
        return "BRAZIL_INELIGIBLE"
    if op.cost == Cost.REQUIRED:
        return "INVESTMENT_REQUIRED"
    if op.cost == Cost.GAS or op.evidence.get("taxas_confirmadas"):
        return "CONDITIONAL_COST"
    if (verified_alert(op) and op.evidence.get("resgate_sem_taxas")
            and not op.evidence.get("custos_ambiguos")):
        return "ZERO_INVESTMENT_CONFIRMED"
    if op.official and (op.cost == Cost.FREE or op.evidence.get("gratuidade")):
        return "ZERO_INVESTMENT_UNCONFIRMED"
    return "INSUFFICIENT_EVIDENCE"
