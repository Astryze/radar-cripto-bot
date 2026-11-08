import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from scripts.audit_sources import audit
from src.feed_reader import load_sources, parse_json_source
from src.main import run
from src.models import Cost
from src.opportunity_filter import classify
from src.state import State
from src.utils import HttpClient


def test_registered_coverage_and_discovery_provenance():
    sources = load_sources(Path("config/sources.json"))
    assert {"arbitrum", "base", "polygon", "zksync", "scroll", "bitdegree-official-guild"} <= {s.id for s in sources}
    assert all(s.discovered_from for s in sources)
    assert all(s.url.startswith("https://") for s in sources)


def test_known_public_json_schema_only(source):
    source.kind = "json"
    source.items_path = "data.campaigns"
    result = parse_json_source(json.dumps({"data": {"campaigns": [
        {"title": "Learn and earn quiz", "url": "https://example.org/quiz", "description": "Earn 10 USDC"},
        {"title": "Unsafe", "url": "https://evil.test/claim"}]}}), source)
    assert len(result) == 1 and not result[0].verified


def test_api_schema_mismatch_fails(source):
    with pytest.raises(ValueError):
        parse_json_source('{"message":"not a campaign list"}', source)


def test_audit_records_http_and_collection_date(source, response):
    source.kind = "page"
    session = Mock()
    session.get.return_value = response(data=b'<article><h1>Learn &amp; Earn Mission</h1>Public campaign.</article>')
    result = audit([source], HttpClient(session, Mock()))[0]
    assert result["http_status"] == 200 and result["last_collected_at"]
    assert result["collectable"]


def test_cooldown_persists_between_runs(source, response, tmp_path):
    session = Mock()
    session.get.return_value = response(status=429, headers={"Retry-After": "3600"})
    state = State(tmp_path / "state.json")
    assert run([source], HttpClient(session, Mock()), state, Mock(), tmp_path / "reports") == 2
    second_session = Mock()
    assert run([source], HttpClient(second_session, Mock()), State(state.path), Mock(), tmp_path / "reports") == 2
    second_session.get.assert_not_called()
    assert state.data["source_health"][source.id]["http_status"] == 429


def test_incomplete_rules_do_not_confirm_free(candidate, now):
    c = candidate("No purchase or deposit required.")
    c.investigation_errors = ["FetchError"]
    assert classify(c, now).cost == Cost.POSSIBLE
