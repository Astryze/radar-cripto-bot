import argparse
import logging
import os
import time
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .feed_reader import load_sources, read_source, verify_candidate
from .opportunity_filter import classify, is_opportunity
from .scoring import score
from .state import State
from .telegram_bot import TelegramBot, daily_summary, opportunity_message
from .utils import FetchError, HttpClient, atomic_json, canonical_url, parse_date, setup_logging, utcnow

LOG = logging.getLogger(__name__)


def failure_reason(exc):
    return str(exc) if isinstance(exc, FetchError) else type(exc).__name__


def run(sources, client, state, bot, report_dir, dry_run=False, max_alerts=10, budget_seconds=600):
    from dataclasses import replace
    from .investigation import investigate
    from .opportunity_filter import deadline_info
    from .models import Candidate, Opportunity
    from .utils import DeferredFetch
    started, clock = utcnow(), time.monotonic()
    errors, opportunities, health, seen = [], [], [], set()
    sent = 0
    official_domains = {d for s in sources if s.official for d in s.domains}
    if isinstance(client, HttpClient):
        client.cooldowns.update(state.data["cooldowns"])
    for source in (s for s in sources if s.enabled):
        if time.monotonic() - clock > budget_seconds:
            errors.append("Orçamento de execução esgotado; cobertura parcial")
            break
        prior_health = state.data["source_health"].get(source.id, {})
        status = {"id": source.id, "ok": False, "candidates": 0, "analyzed": 0,
                  "last_attempt_at": utcnow().isoformat(), "last_collected_at": prior_health.get("last_collected_at"),
                  "http_status": None, "status": "unavailable"}
        health.append(status)
        start_records = len(client.records) if isinstance(client, HttpClient) else 0
        if isinstance(client, HttpClient):
            client.min_interval = source.min_interval_seconds
        pending = state.data["pending_sources"].get(source.id)
        effective = replace(source, url=pending["url"]) if pending else source
        try:
            candidates = read_source(effective, client)
            status.update(ok=True, candidates=len(candidates), status="collected", last_collected_at=utcnow().isoformat())
            if not dry_run:
                state.data["pending_sources"].pop(source.id, None)
            LOG.info("Fonte %s: %s candidatos", source.id, len(candidates))
        except DeferredFetch as exc:
            status.update(status="pending" if exc.status == 202 else "cooldown", http_status=exc.status,
                          next_retry_at=exc.next_retry_at)
            if exc.monitor_url and not dry_run:
                state.data["pending_sources"][source.id] = {"url": exc.monitor_url, "next_retry_at": exc.next_retry_at}
            if exc.status != 202:
                errors.append(f"{source.id}: {failure_reason(exc)}")
            LOG.warning("Fonte %s: %s", source.id, failure_reason(exc))
            candidates = []
        except Exception as exc:
            errors.append(f"{source.id}: coleta {failure_reason(exc)}")
            LOG.warning("Fonte %s falhou: %s", source.id, failure_reason(exc))
            candidates = []
        if isinstance(client, HttpClient):
            records = client.records[start_records:]
            if records:
                status.update(http_status=records[-1]["status"], effective_url=records[-1]["url"],
                              http_attempts=len(records), content_type=records[-1]["content_type"])
        # Reconsultar algumas campanhas históricas ausentes da listagem (inclusive fechamento).
        if status["ok"]:
            listed = {canonical_url(c.url) for c in candidates}
            tracked = [r["latest"] for url, r in sorted(state.data["campaigns"].items(), key=lambda item: item[1].get("last_checked", item[1].get("last_seen", "")))
                       if r.get("latest", {}).get("source_id") == source.id and url not in listed
                       and r["latest"].get("deadline") != "encerrado"][:3]
            candidates.extend(Candidate(r["title"], r["url"], source) for r in tracked)
        verification_failures = 0
        investigation_failures = 0
        for candidate in candidates:
            if time.monotonic() - clock > budget_seconds:
                errors.append(f"{source.id}: tempo de verificação esgotado")
                break
            key = canonical_url(candidate.url)
            if key in seen:
                continue
            if source.kind in {"feed", "json"} and not is_opportunity(candidate.title, candidate.text):
                continue
            seen.add(key)
            if not dry_run and key in state.data["campaigns"]:
                state.data["campaigns"][key]["last_checked"] = utcnow().isoformat()
            try:
                candidate = verify_candidate(candidate, client)
                published = parse_date(candidate.published)
                if published and (published < started - timedelta(days=source.max_age_days)
                                  or published > started + timedelta(days=1)):
                    continue
                candidate = investigate(candidate, client, official_domains, max_pages=3)
                if candidate.investigation_errors:
                    investigation_failures += len(candidate.investigation_errors)
            except Exception as exc:
                verification_failures += 1
                errors.append(f"{source.id}: página de campanha {failure_reason(exc)}")
                candidate.verified = False
            op = classify(candidate, now=started)
            if op is None and candidate.verified:
                prior = state.data["campaigns"].get(key, {}).get("latest")
                closed, end, _ = deadline_info(candidate.text, candidate.listing_status, started)
                if prior and closed == "encerrado":
                    op = Opportunity(**{k: v for k, v in prior.items() if k in Opportunity.__dataclass_fields__})
                    op.deadline, op.deadline_at, op.conclusion = "encerrado", end or op.deadline_at, "ENCERRADA"
            if op is not None:
                opportunities.append(score(op))
                status["analyzed"] += 1
            if verification_failures >= 3:
                status["ok"] = False
                status["status"] = "partial"
                errors.append(f"{source.id}: verificação suspensa após três falhas; cobertura parcial")
                break
        status["verification_failures"] = verification_failures
        status["investigation_failures"] = investigation_failures
    merged = {}
    for op in opportunities:
        key = canonical_url(op.url)
        old = merged.get(key)
        if old is None or (op.official, len(op.investigated_urls), op.score) > (old.official, len(old.investigated_urls), old.score):
            merged[key] = op
    # Prazo oficial guardado também expira quando uma fonte está indisponível.
    for key, record in state.data["campaigns"].items():
        old = record.get("latest", {})
        end = parse_date(old.get("deadline_at"))
        if key not in merged and end and end < started and old.get("deadline") != "encerrado":
            op = Opportunity(**{k: v for k, v in old.items() if k in Opportunity.__dataclass_fields__})
            op.deadline, op.conclusion = "encerrado", "ENCERRADA"
            merged[key] = score(op)
    opportunities = sorted(merged.values(), key=lambda o: (-o.score, o.url))
    day = started.astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    new_count = sum(canonical_url(op.url) not in state.data["campaigns"] for op in opportunities)
    events = [(op, state.event(op)) for op in opportunities]
    unavailable = sum(not h["ok"] and h["status"] != "pending" for h in health)
    pending_count = sum(h["status"] == "pending" for h in health)
    summary = daily_summary(opportunities, errors, day, len(health), new_count, unavailable, pending_count)
    if not dry_run:
        for op, event in events:
            state.observe(op, event)
        state.data["source_health"].update({h["id"]: h for h in health})
        if isinstance(client, HttpClient):
            state.data["cooldowns"] = client.cooldowns
        state.save()
        delivery_ok = True
        if not state.summary_sent(day):
            try:
                bot.send(summary)
                state.mark_summary(day)
            except Exception as exc:
                delivery_ok = False
                errors.append(f"Resumo Telegram: {failure_reason(exc)}")
        if delivery_ok:
            for op, event in events:
                if event and sent < max_alerts:
                    try:
                        bot.send(opportunity_message(op, event))
                        state.mark(op)
                        sent += 1
                    except Exception as exc:
                        errors.append(f"Entrega Telegram: {failure_reason(exc)}")
                        break
    result = {"version": "2.0", "started_at": started.isoformat(), "finished_at": utcnow().isoformat(),
              "dry_run": dry_run, "sent": sent, "new_campaigns": new_count, "sources": health, "errors": errors,
              "pending_sources": pending_count,
              "http_records": client.records if isinstance(client, HttpClient) else [],
              "events": [{"url": op.url, "event": event} for op, event in events if event],
              "opportunities": [o.to_dict() for o in opportunities]}
    atomic_json(Path(report_dir) / "run.json", result)
    atomic_json(Path(report_dir) / "source-health.json", health)
    Path(report_dir, "summary.txt").write_text(summary, encoding="utf-8")
    for error in errors:
        LOG.warning("Falha registrada: %s", error)
    LOG.info("Concluído: %d campanhas, %d alertas, %d falhas; %d fontes pendentes", len(opportunities), sent, len(errors), pending_count)
    return 2 if errors else 0


def main():
    parser = argparse.ArgumentParser(description="Radar de campanhas públicas com zero investimento")
    parser.add_argument("--dry-run", action="store_true", help="Pesquisa sem enviar Telegram nem alterar estado")
    parser.add_argument("--sources", type=Path, default=Path("config/sources.json"))
    parser.add_argument("--state", type=Path, default=Path("state/radar.json"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    args = parser.parse_args()
    setup_logging("logs")
    try:
        sources = load_sources(args.sources)
        if not any(s.enabled for s in sources):
            raise ValueError("Nenhuma fonte habilitada")
        state = State(args.state)
        bot = None if args.dry_run else TelegramBot(os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID"))
        return run(sources, HttpClient(), state, bot, args.reports, args.dry_run)
    except Exception as exc:
        LOG.error("Execução interrompida: %s", type(exc).__name__)
        atomic_json(args.reports / "failure.json", {"at": utcnow().isoformat(), "error_type": type(exc).__name__,
                     "hint": "Verifique fontes, estado e presença dos dois GitHub Secrets. Credenciais nunca são registradas."})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
