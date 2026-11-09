import json
from unittest.mock import Mock

import pytest
import requests

from src.feed_reader import verify_candidate
from src.main import run
from src.models import Candidate, Source
from src.state import State
from src.utils import HttpClient, ResponseTooLarge


def test_solana_429_continues_and_keeps_partial_status(response, tmp_path):
    solana = Source('solana', 'Solana', 'https://solana.com/news', 'page', ['solana.com'])
    other = Source('other', 'Other', 'https://example.org/news', 'page', ['example.org'])
    session = Mock()
    session.get.side_effect = [
        response(status=429, headers={'Retry-After': '3600'}),
        response(data=b'<article><h1>Public update</h1>Official news. ' + b'Details. ' * 20 + b'</article>'),
    ]
    client = HttpClient(session, Mock())
    assert run([solana, other], client, State(tmp_path / 'state'), None,
               tmp_path, dry_run=True, allow_partial=True) == 0
    result = json.loads((tmp_path / 'run.json').read_text())
    assert result['collection_status'] == 'partial' and result['sources'][1]['listing_collected']
    report = json.loads((tmp_path / 'integrations/solana.json').read_text())
    assert report['status'] == 'cooldown' and report['http_status'] == 429
    assert report['http_records'][0]['retry_after_seconds'] == 3600
    assert session.get.call_count == 2


@pytest.mark.parametrize('recovery', [True, False])
def test_polygon_fallback_reads_complete_article_with_ceiling(response, recovery):
    source = Source('polygon', 'Polygon', 'https://polygon.technology/blog', 'listing', ['polygon.technology'])
    candidate = Candidate('Example', source.url + '/example', source)
    article = b'<article><h1>Official update</h1><p>' + b'Public details. ' * 10 + b'</p></article>'
    session = Mock()
    session.get.side_effect = [
        response(data=b'x' * 2_000_001),
        response(data=article + b' ' * (2_000_001 if recovery else 4_000_001)),
    ]
    client = HttpClient(session, Mock())
    if recovery:
        assert verify_candidate(candidate, client).verified
    else:
        with pytest.raises(ResponseTooLarge, match='4 MB'):
            verify_candidate(candidate, client)
        assert not candidate.verified
    assert client.records[0]['error'] == 'response_too_large'
    assert client.records[1]['fallback'] == 'polygon_full_article_4mb'


def test_read_timeout_retries_and_preserves_http_evidence(response):
    interrupted = response()
    interrupted.iter_content.side_effect = requests.ReadTimeout('private error')
    session, sleep = Mock(), Mock()
    session.get.side_effect = [interrupted, response(data=b'complete')]
    client = HttpClient(session, sleep, jitter=lambda: 0)
    assert client.get('https://example.org/article', ['example.org'])[0] == b'complete'
    assert client.records[0]['status'] == 200 and client.records[0]['error'] == 'timeout'
    assert 'private error' not in json.dumps(client.records)
    sleep.assert_called_once_with(1)


def test_allow_partial_does_not_hide_delivery_failure(source, response, tmp_path):
    source.kind = 'page'
    session = Mock()
    session.get.return_value = response(data=b'<article><h1>News</h1>' + b'Public details. ' * 10 + b'</article>')
    bot = Mock()
    bot.send.side_effect = RuntimeError
    assert run([source], HttpClient(session, Mock()), State(tmp_path / 'state'),
               bot, tmp_path, allow_partial=True) == 2
    assert json.loads((tmp_path / 'run.json').read_text())['delivery_failed']
