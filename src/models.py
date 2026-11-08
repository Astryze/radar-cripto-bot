from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Cost(StrEnum):
    FREE = "GRATUITA CONFIRMADA"
    GAS = "GRATUITA COM TAXA DE REDE"
    POSSIBLE = "PODE EXIGIR INVESTIMENTO"
    REQUIRED = "EXIGE INVESTIMENTO"
    UNKNOWN = "NÃO CONFIRMADA"


@dataclass
class Source:
    id: str
    name: str
    url: str
    kind: str
    domains: list[str]
    official: bool = True
    enabled: bool = True
    selector: str = "a[href]"
    path_pattern: str = ".*"
    max_items: int = 15
    max_age_days: int = 90


@dataclass
class Candidate:
    title: str
    url: str
    source: Source
    text: str = ""
    published: str | None = None
    listing_status: str = ""
    verified: bool = False
    verification_url: str = ""
    listing_text: str = ""


@dataclass
class Opportunity:
    title: str
    project: str
    url: str
    cost: Cost = Cost.UNKNOWN
    reward: str = "Não informada"
    reward_status: str = "desconhecida"
    reward_type: str = "desconhecida"
    deadline: str = "não confirmado"
    deadline_at: str | None = None
    eligibility: str = "desconhecida"
    kyc: str = "não informado"
    effort: str = "alto"
    priority: str = "baixa"
    score: int = 0
    official: bool = False
    confidence: str = "baixa"
    steps: list[str] = field(default_factory=list)
    evidence: dict[str, list[str]] = field(default_factory=dict)
    source_url: str = ""
    published: str | None = None

    def to_dict(self):
        return asdict(self)
