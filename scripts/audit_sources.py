"""Audita endpoints configurados, sem inventar feeds/APIs ou usar credenciais."""
import argparse
from pathlib import Path

from src.feed_reader import load_sources, read_source
from src.utils import DeferredFetch, HttpClient, atomic_json, utcnow


def audit(sources, client):
    results = []
    for source in sources:
        before = len(client.records)
        entry = {"id": source.id, "url": source.url, "kind": source.kind,
                 "discovered_from": source.discovered_from, "checked_at": utcnow().isoformat(),
                 "http_status": None, "collectable": False}
        try:
            candidates = read_source(source, client)
            entry.update(collectable=True, items=len(candidates), last_collected_at=utcnow().isoformat())
        except DeferredFetch as exc:
            entry.update(status="pending" if exc.status == 202 else "cooldown", http_status=exc.status,
                         next_retry_at=exc.next_retry_at)
        except Exception as exc:
            entry["error_type"] = type(exc).__name__
        records = client.records[before:]
        if records:
            entry.update(http_status=records[-1]["status"], effective_url=records[-1]["url"],
                         content_type=records[-1]["content_type"], requests=len(records))
        results.append(entry)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=Path("config/sources.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/source-audit.json"))
    args = parser.parse_args()
    atomic_json(args.output, audit(load_sources(args.sources), HttpClient(min_interval=0.5)))
