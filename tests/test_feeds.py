from datetime import timedelta

import pytest
from defusedxml.common import DefusedXmlException

from src.bitdegree import parse_learndrops
from src.feed_reader import parse_feed, parse_listing, verify_candidate


def rss(link="https://example.org/quest", date="Sun, 08 Nov 2026 00:00:00 GMT"):
    return f"""<rss version="2.0"><channel><item><title>Quiz Campaign</title><link>{link}</link>
    <description>Join the quest to earn rewards.</description><pubDate>{date}</pubDate></item></channel></rss>""".encode()


def test_rss(source, now):
    result = parse_feed(rss(), source, now)
    assert len(result) == 1 and result[0].published.startswith("2026-11-08")
    assert not result[0].verified


def test_atom_alternate_link(source, now):
    xml = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Campaign</title>
    <link rel="self" href="https://evil.test/self"/><link rel="alternate" href="https://example.org/quest"/>
    <summary>Join to earn token rewards.</summary><updated>2026-11-08T01:00:00Z</updated></entry></feed>'''
    result = parse_feed(xml, source, now)
    assert result[0].url == "https://example.org/quest"


def test_html_not_feed(source):
    with pytest.raises(ValueError):
        parse_feed(b"<html><body>Not RSS</body></html>", source)


def test_xxe(source):
    with pytest.raises(DefusedXmlException):
        parse_feed(b'<!DOCTYPE rss [<!ENTITY leak SYSTEM "file:///etc/passwd">]><rss>&leak;</rss>', source)


def test_foreign_link_rejected(source, now):
    assert parse_feed(rss("https://example.org.evil.test/quest"), source, now) == []


def test_old_and_future_date(source, now):
    assert parse_feed(rss(date="Sun, 01 Jan 2023 00:00:00 GMT"), source, now) == []
    assert parse_feed(rss(), source, now - timedelta(days=3)) == []


def test_missing_date_is_unknown(source, now):
    assert parse_feed(rss(date="TBA"), source, now)[0].published is None


def test_feed_deduplication(source, now):
    xml = rss().decode().replace("</channel>", rss().decode().split("<channel>")[1].split("</channel>")[0] + "</channel>")
    assert len(parse_feed(xml.encode(), source, now)) == 1


def test_bitdegree_card_status_and_internal_tabs(source):
    source.url = "https://example.org/learndrops"
    html = b'''<a href="/leaderboard">Crypto Airdrops</a>
    <div class="promotional-card"><a href="/guilds/project/mission">Status: Ended</a>
    <a href="/guilds/project/mission"><h2>Example Learn &amp; Earn</h2></a>
    <p>Collect Bits. Event end date: October 28, 2026</p>
    <a href="/guilds/project/mission?section=prize-pool">See Rewards</a></div>'''
    result = parse_learndrops(html, source)
    assert len(result) == 1 and result[0].listing_status == "encerrado"
    assert result[0].title == "Example Learn & Earn"
    assert "October" in result[0].listing_text


def test_bitdegree_empty_fails(source):
    with pytest.raises(ValueError):
        parse_learndrops(b"<html>Login needed</html>", source)


def test_listing(source):
    source.selector = "h2 a[href]"
    source.path_pattern = r"/quest/"
    result = parse_listing(b'<h2><a href="/quest/one">Mission one</a></h2><a href="/quest/two">Ignored</a>', source)
    assert len(result) == 1


def test_verify_does_not_use_navigation_promises(candidate):
    from unittest.mock import Mock
    c = candidate("FREE FREE FREE")
    body = b'<html><nav>No purchase or deposit required.</nav><article><h1>Quest</h1><p>Join the quiz mission to earn rewards. Deposit is required to qualify. Read all conditions before entering.</p></article></html>'
    client = Mock()
    client.get.return_value = body, c.url, "text/html"
    result = verify_candidate(c, client)
    assert result.verified and "No purchase" not in result.text
    assert "Deposit" in result.text


def test_listing_relative_links_use_redirect_target(source):
    from unittest.mock import Mock
    from src.feed_reader import read_source
    source.kind = "listing"
    source.domains.append("official.example.org")
    client = Mock()
    client.get.return_value = (b'<a href="/quest">Official quiz mission</a>',
                              "https://official.example.org/list", "text/html")
    assert read_source(source, client)[0].url == "https://official.example.org/quest"
