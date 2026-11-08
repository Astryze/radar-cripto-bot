from unittest.mock import Mock

import pytest

from src.investigation import investigate
from src.models import Candidate, Conclusion, Cost
from src.opportunity_filter import classify


def test_follow_campaign_rules_to_disambiguate(candidate, now):
    c = candidate("Rules are available below.")
    c.links = [{"url": c.url + "/rules", "label": "Mission rules"}]
    client = Mock()
    client.get.return_value = (b'<article>Official mission rules: Join now. No purchase or deposit required. Complete the quiz to earn 20 USDC. Brazil is eligible.</article>',
                               c.url + "/rules", "text/html")
    investigate(c, client, {"example.org"})
    op = classify(c, now)
    assert op.cost == Cost.FREE
    assert c.url + "/rules" in op.investigated_urls


def test_aggregator_cannot_prove_free_route(candidate, now):
    c = candidate("No purchase or deposit required.", verified=False)
    c.links = [{"url": c.url + "/rules", "label": "Rules"}]
    client = Mock()
    investigate(c, client, {"example.org"})
    assert classify(c, now).conclusion == Conclusion.UNKNOWN
    client.get.assert_not_called()


def test_global_terms_not_promoted_to_campaign_rules(candidate):
    c = candidate("Join the mission.")
    c.links = [{"url": "https://example.org/terms", "label": "Terms and conditions"},
               {"url": "https://evil.test/mission/rules", "label": "Example Learn Earn Mission Rules"}]
    client = Mock()
    investigate(c, client, {"example.org"})
    client.get.assert_not_called()


@pytest.mark.parametrize("required,expected", [(False, Cost.FREE), (True, Cost.REQUIRED)])
def test_explicit_complete_alternative_route(candidate, now, required, expected):
    c = candidate("Paid route: Deposit $10 to enter.\n\nAlternative free entry: Complete the quiz. No purchase or deposit required.")
    if required:
        c.text += "\nAll participants must deposit $10."
    assert classify(c, now).cost == expected


def bitdegree_candidate(source):
    source.url = "https://www.bitdegree.org/learndrops"
    source.domains = ["www.bitdegree.org"]
    source.policy_urls = ["https://www.bitdegree.org/faq"]
    c = Candidate("Ledger Mission", "https://www.bitdegree.org/guilds/ledger/mission", source,
                  "Mission\nLearn and collect Bits!\nRounds\nRead the article\nAnswer the quiz", listing_status="aberto", verified=True)
    c.documents = [{"url": c.url, "text": c.text, "scope": "campaign", "official": True},
                   {"url": "https://www.bitdegree.org/faq", "text": "All BitDegree Missions are free of charge.", "scope": "platform_policy", "official": True}]
    return c


def test_bitdegree_free_points_not_guaranteed_crypto(source, now):
    op = classify(bitdegree_candidate(source), now)
    assert op.cost == Cost.FREE
    assert op.conclusion == Conclusion.UNCERTAIN
    assert op.token == "não informado" and op.estimated_value == "não verificável"
    assert "faq" in op.evidence["politica_oficial"][0]


def test_policy_cannot_override_mandatory_deposit(source, now):
    c = bitdegree_candidate(source)
    c.text += "\nYou must deposit $50 to qualify."
    c.documents[0]["text"] = c.text
    assert classify(c, now).cost == Cost.REQUIRED


def test_policy_cannot_apply_to_external_project(source, now):
    c = bitdegree_candidate(source)
    c.url = "https://external.test/mission"
    assert classify(c, now).cost == Cost.POSSIBLE


def test_user_created_mission_never_confirmed(source, now):
    from src.bitdegree import parse_learndrops
    source.official = False
    source.trusted_guilds = ["bitdegree"]
    cards = b'<a href="/guilds/random/mission"><h2>My reward Mission</h2></a>'
    c = parse_learndrops(cards, source)[0]
    assert not c.source.official


@pytest.mark.parametrize("text,conclusion", [
    ("No purchase or deposit required. KYC is required.", Conclusion.KYC),
    ("No purchase or deposit required. You may win a prize in a raffle.", Conclusion.UNCERTAIN),
    ("No purchase or deposit required. Network fees apply.", Conclusion.GAS),
    ("Deposit $10 to claim.", Conclusion.REQUIRED),
    ("This campaign has ended.", Conclusion.CLOSED),
])
def test_conclusions(candidate, now, text, conclusion):
    assert classify(candidate(text), now).conclusion == conclusion


def test_token_pool_never_becomes_personal_reward(candidate, now):
    op = classify(candidate("Join the campaign to share a total reward pool of 10000 USDC. No purchase or deposit required."), now)
    assert op.token == "USDC"
    assert "pool total" in op.token_quantity
    assert op.withdrawability == "não confirmada"


def test_free_testnet_requires_explicit_no_real_funds(candidate, now):
    op = classify(candidate("Join the testnet campaign. Test tokens have no monetary value. Use the free faucet. No real funds are required. Claim potential rewards."), now)
    assert op.cost == Cost.FREE and op.conclusion == Conclusion.UNCERTAIN


def test_costly_testnet_cannot_hide_mainnet_deposit(candidate, now):
    op = classify(candidate("Join the testnet campaign. Test tokens have no value. Free faucet. No real funds are required. You must deposit on mainnet."), now)
    assert op.cost == Cost.REQUIRED
