from unittest.mock import Mock

from src.feed_reader import verify_candidate
from src.investigation import investigate
from src.models import Candidate, Cost
from src.opportunity_filter import classify
from src.scoring import score
from src.telegram_bot import daily_summary, opportunity_message


def test_known_guild_remains_official_during_historical_recheck(source):
    source.kind = "bitdegree"
    source.official = False
    source.domains = ["www.bitdegree.org"]
    source.trusted_guilds = ["ledger"]
    c = Candidate("Ledger Mission", "https://www.bitdegree.org/guilds/ledger/mission", source)
    client = Mock()
    client.get.return_value = (b'<article>Mission: Learn about security and collect Bits. Complete the educational quiz and read our public learning material.</article>', c.url, "text/html")
    assert verify_candidate(c, client).verified


def test_other_users_guild_cannot_supply_rules(source):
    source.domains = ["www.bitdegree.org"]
    c = Candidate("Ledger Security Mission", "https://www.bitdegree.org/guilds/ledger/mission", source,
                  "Learn and collect Bits.", verified=True)
    c.links = [{"url": "https://www.bitdegree.org/guilds/random/ledger-security-rules", "label": "Ledger security rules"}]
    client = Mock()
    investigate(c, client, {"www.bitdegree.org"})
    client.get.assert_not_called()


def test_free_route_not_blocked_by_global_free_registration(candidate, now):
    c = candidate("All participants must register.\nPaid route: Deposit $10 to enter.\n\nAlternative free entry: Complete the quiz. No purchase or deposit required.")
    assert classify(c, now).cost == Cost.FREE


def test_account_specific_eligibility_not_high_priority(candidate, now):
    c = candidate("No purchase or deposit required. Brazil is eligible. New users only.")
    op = score(classify(c, now))
    assert op.eligibility_requirements and op.priority != "alta"
    assert "%" not in op.eligibility_basis


def test_telegram_distinguishes_points_and_uncertain_rewards(candidate, now):
    op = classify(candidate("No purchase or deposit required. Collect Bits for a chance to win tokens."), now)
    message = opportunity_message(op)
    assert "RECOMPENSA INCERTA" in message and "não equivalem" in message
    assert "Saque/negociação: não confirmada" in message
    summary = daily_summary([op], [], "2026-11-08", 16, new_count=1, unavailable=0, pending_count=1)
    assert "Novas campanhas encontradas: 1" in summary
    assert "Fontes aguardando resultado (202): 1" in summary


def test_announced_new_symbol_and_points_never_convert(candidate, now):
    op = classify(candidate("No purchase or deposit required. Earn 25 TURTLE tokens and collect 1000 XP."), now)
    assert op.token == "TURTLE" and "25" in op.token_quantity
    assert op.estimated_value == "não verificável"
    assert "pontos internos" in op.reward_type


def test_portuguese_deadline(candidate, now):
    op = classify(candidate("No purchase or deposit required. Encerramento: 7 de novembro de 2026."), now)
    assert op.deadline == "encerrado" and op.deadline_at.startswith("2026-11-07")


def test_daily_highlights_do_not_repeat_unchanged_campaigns(candidate, now):
    op = classify(candidate("No purchase or deposit required."), now)
    summary = daily_summary([op], [], "2026-11-09", 16, highlight_urls=set())
    assert op.url not in summary and op.title not in summary
    assert "Gratuitas confirmadas: 1" in summary


def test_unverified_country_and_expiry_claims_are_not_official(candidate, now):
    op = classify(candidate("Brazil is eligible. KYC is required. This campaign has ended.", verified=False), now)
    assert op.eligibility == "desconhecida" and op.kyc == "não confirmado"
    assert op.conclusion == "NÃO CONFIRMADA"
