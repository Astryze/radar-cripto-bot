import pytest

from src.models import Cost
from src.opportunity_filter import classify


@pytest.mark.parametrize("text,expected", [
    ("Free to participate. Staking optional and deposit required.", Cost.REQUIRED),
    ("Free to participate. Staking optional, minimum balance required.", Cost.REQUIRED),
    ("Free to participate. You must hold 100 tokens.", Cost.REQUIRED),
    ("Free to participate. You must own an NFT.", Cost.REQUIRED),
    ("Free to participate. You must pay network fees.", Cost.GAS),
])
def test_hidden_requirements(candidate, now, text, expected):
    assert classify(candidate(text), now).cost == expected
