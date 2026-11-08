from .models import Cost


def score(op):
    value = {Cost.FREE: 45, Cost.GAS: 15, Cost.POSSIBLE: 0,
             Cost.REQUIRED: -100, Cost.UNKNOWN: -20}[op.cost]
    value += {"baixo": 15, "médio": 5, "alto": 0}[op.effort]
    value += 10 if op.official else 0
    value += {"confirmada": 10, "estimada": 3, "desconhecida": 0}[op.reward_status]
    value += 10 if op.deadline == "aberto" else 0
    value += 10 if op.eligibility == "Brasil confirmado" else 0
    if op.deadline == "encerrado" or "pausa" in op.evidence or op.eligibility == "Brasil não elegível":
        value = 0
    op.score = max(0, min(100, value))
    op.priority = "baixa"
    if (op.cost == Cost.FREE and op.official and op.deadline == "aberto"
            and op.eligibility == "Brasil confirmado" and op.reward_status == "confirmada"
            and op.effort == "baixo" and op.score >= 85):
        op.priority = "alta"
        op.confidence = "alta"
    elif (op.cost in {Cost.FREE, Cost.GAS} and op.score >= 40
          and op.deadline != "encerrado" and "pausa" not in op.evidence
          and op.eligibility != "Brasil não elegível"):
        op.priority = "média"
    return op


def actionable(op):
    return (op.cost == Cost.FREE and op.official and op.deadline == "aberto"
            and op.eligibility != "Brasil não elegível" and "pausa" not in op.evidence)
