import pytest

from src.models import Cost
from src.opportunity_filter import classify, is_opportunity


@pytest.mark.parametrize("text,expected", [
    ("Free airdrop rewards!", Cost.POSSIBLE),
    ("No purchase or deposit required.", Cost.FREE),
    ("Participation is completely free.", Cost.FREE),
    ("Free to participate. KYC is required.", Cost.FREE),
    ("No purchase or deposit required. Staking is optional.", Cost.FREE),
    ("No purchase or deposit required. Staking is not required.", Cost.FREE),
    ("No purchase or deposit required. No staking required.", Cost.FREE),
    ("Free to participate. Gas fees apply.", Cost.GAS),
    ("Free to participate. Use mainnet. Gas fees apply.", Cost.GAS),
    ("Free to participate. Gas fees are sponsored.", Cost.FREE),
    ("Free to participate. A deposit is required.", Cost.REQUIRED),
    ("Free to participate. You must buy tokens.", Cost.REQUIRED),
    ("No purchase or deposit required. You must stake 10 tokens.", Cost.REQUIRED),
    ("Free to participate. Minimum balance: 10 tokens.", Cost.REQUIRED),
    ("Free to participate. A subscription is mandatory.", Cost.REQUIRED),
    ("Free to participate. You must pay a registration fee.", Cost.REQUIRED),
    ("Free to participate. Deposit $10 to claim.", Cost.REQUIRED),
    ("No purchase required, deposit required.", Cost.REQUIRED),
    ("No purchase required but deposit required.", Cost.REQUIRED),
    ("No purchase required. Deposit is optional.", Cost.POSSIBLE),
    ("Participation is free. Staking rewards available.", Cost.POSSIBLE),
    ("Free to participate. Complete a swap on mainnet.", Cost.POSSIBLE),
    ("Participação é gratuita. Depósito obrigatório.", Cost.REQUIRED),
    ("Participação é gratuita. Staking opcional.", Cost.FREE),
])
def test_costs(candidate, now, text, expected):
    op = classify(candidate(text), now)
    assert op.cost == expected
    if op.cost == Cost.FREE:
        assert op.evidence["gratuidade"]


def test_aggregator_never_proves_free(candidate, now):
    op = classify(candidate("No purchase or deposit required.", verified=False), now)
    assert op.cost == Cost.UNKNOWN
    assert op.reward_status == "desconhecida"


@pytest.mark.parametrize("title,text,expected", [
    ("Airdrop market update", "The token price went up yesterday.", False),
    ("What is an airdrop?", "Complete quests to earn rewards.", False),
    ("Airdrop scam warning", "Claim tokens and get rewards.", False),
    ("New token distribution", "Join this campaign and complete the quiz to earn rewards.", True),
    ("Testnet update", "The testnet was upgraded for developers.", False),
    ("Casino Quest", "Join now to earn rewards in the casino.", False),
    ("History of airdrops", "People earn rewards in a campaign.", False),
])
def test_context(title, text, expected):
    assert is_opportunity(title, text) == expected


@pytest.mark.parametrize("text,status,date", [
    ("Deadline: November 7, 2026", "encerrado", "2026-11-07"),
    ("Event end date: November 9, 2026", "aberto", "2026-11-09"),
    ("Ends on 2026-11-09", "aberto", "2026-11-09"),
    ("Prazo: 09/11/2026", "aberto", "2026-11-09"),
    ("Registration is closed.", "encerrado", None),
    ("Campaign ended.", "encerrado", None),
    ("Mission is currently on pause.", "não confirmado", None),
])
def test_deadline(candidate, now, text, status, date):
    op = classify(candidate(text), now)
    assert op.deadline == status
    assert op.deadline_at is None if date is None else op.deadline_at.startswith(date)


def test_no_deadline_without_evidence(candidate, now):
    c = candidate("Participate sometime. No purchase or deposit required.")
    c.text = c.text.replace("Join now.", "")
    assert classify(c, now).deadline == "não confirmado"


def test_listing_deadline_survives_verification(candidate, now):
    c = candidate("No purchase or deposit required.")
    c.listing_status = "aberto"
    c.listing_text = "Event end date: October 28, 2026"
    assert classify(c, now).deadline == "encerrado"


@pytest.mark.parametrize("text,expected", [
    ("Brazil is eligible.", "Brasil confirmado"),
    ("Available in Brazil.", "Brasil confirmado"),
    ("Brazil is not eligible.", "Brasil não elegível"),
    ("Not available in Brazil.", "Brasil não elegível"),
    ("Residents of Brazil are not eligible.", "Brasil não elegível"),
    ("Restricted countries: USA, Brazil, Canada.", "Brasil não elegível"),
    ("Worldwide campaign. Restrictions apply.", "desconhecida"),
])
def test_brazil(candidate, now, text, expected):
    assert classify(candidate(text), now).eligibility == expected


def test_bits_not_cash(candidate, now):
    op = classify(candidate("Collect Bits in this mission. No purchase or deposit required."), now)
    assert "pontos internos" in op.reward_type
    assert "não equivalem" in op.reward_type


def test_kyc_not_money(candidate, now):
    op = classify(candidate("KYC is required. No purchase or deposit required."), now)
    assert op.cost == Cost.FREE
    assert "obrigatório" in op.kyc
