from dataclasses import asdict, dataclass, field
from enum import StrEnum


class Cost(StrEnum):
    FREE = "GRATUITA CONFIRMADA"
    GAS = "GRATUITA COM TAXA DE REDE"
    POSSIBLE = "PODE EXIGIR INVESTIMENTO"
    REQUIRED = "EXIGE INVESTIMENTO"
    UNKNOWN = "NÃO CONFIRMADA"


class Conclusion(StrEnum):
    FREE = "GRATUITA CONFIRMADA"
    GAS = "GRATUITA COM TAXA DE REDE"
    KYC = "GRATUITA COM REQUISITO DE KYC"
    UNCERTAIN = "GRATUITA, MAS COM RECOMPENSA INCERTA"
    POSSIBLE = "PODE EXIGIR INVESTIMENTO"
    REQUIRED = "EXIGE INVESTIMENTO"
    CLOSED = "ENCERRADA"
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
    policy_urls: list[str] = field(default_factory=list)
    discovered_from: str = ""
    items_path: str = ""
    item_fields: dict[str, str] = field(default_factory=dict)
    min_interval_seconds: float = 0.5
    trusted_guilds: list[str] = field(default_factory=list)


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
    links: list[dict] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)
    investigation_errors: list[str] = field(default_factory=list)


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
    conclusion: str = Conclusion.UNKNOWN
    token: str = "não informado"
    token_quantity: str = "não informada"
    estimated_value: str = "não verificável"
    withdrawability: str = "não confirmada"
    starts_at: str | None = None
    countries: list[str] = field(default_factory=list)
    reward_assets: list[dict] = field(default_factory=list)
    participation_route: str = "Regras completas ainda precisam ser verificadas"
    eligibility_basis: str = "requisitos pessoais não verificados"
    investigated_urls: list[str] = field(default_factory=list)
    investigation_status: str = "não realizada"
    source_id: str = ""
    eligibility_requirements: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)
