import argparse
import logging
import os
import time
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .feed_reader import load_sources, read_source, verify_candidate
from .opportunity_filter import classify, is_opportunity
from .scoring import actionable, score
from .state import State
from .telegram_bot import TelegramBot, daily_summary, opportunity_message
from .utils import FetchError, HttpClient, atomic_json, canonical_url, parse_date, setup_logging, utcnow

LOG = logging.getLogger(__name__)


def failure_reason(exc):
    return str(exc) if isinstance(exc, FetchError) else type(exc).__name__


def run(sources, client, state, bot, report_dir, dry_run=False, max_alerts=10, budget_seconds=600):
    started, clock = utcnow(), time.monotonic()
    errors, opportunities, health, seen = [], [], [], set()
    sent = 0
    for source in (s for s in sources if s.enabled):
        if time.monotonic() - clock > budget_seconds:
            errors.append("Orçamento de execução esgotado; cobertura parcial")
            break
        status = {"id": source.id, "ok": False, "candidates": 0, "analyzed": 0}
        health.append(status)
        try:
            candidates = read_source(source, client)
            status.update(ok=True, candidates=len(candidates))
            LOG.info("Fonte %s: %s candidatos", source.id, len(candidates))
        except Exception as exc:
            # Exceções externas nunca são interpoladas: requests inclui URLs em erros.
            errors.append(f"{source.id}: coleta {failure_reason(exc)}")
            LOG.warning("Fonte %s falhou: %s", source.id, failure_reason(exc))
            continue
        verification_failures = 0
        for candidate in candidates:
            if time.monotonic() - clock > budget_seconds:
                errors.append(f"{source.id}: tempo de verificação esgotado")
                break
            key = canonical_url(candidate.url)
            if key in seen:
                continue
            # Feed fornece pré-filtro; listings precisam da página para descobrir a missão.
            if source.kind == "feed" and not is_opportunity(candidate.title, candidate.text):
                continue
            seen.add(key)
            try:
                candidate = verify_candidate(candidate, client)
                published = parse_date(candidate.published)
                if published and (published < started - timedelta(days=source.max_age_days)
                                  or published > started + timedelta(days=1)):
                    continue
            except Exception as exc:
                verification_failures += 1
                errors.append(f"{source.id}: página de campanha {failure_reason(exc)}")
                LOG.warning("Verificação %s falhou: %s", source.id, failure_reason(exc))
                candidate.verified = False
            op = classify(candidate, now=started)
            if op is not None:
                opportunities.append(score(op))
                status["analyzed"] += 1
            if verification_failures >= 3:
                status["ok"] = False
                errors.append(f"{source.id}: verificação suspensa após três falhas; cobertura parcial")
                break
        status["verification_failures"] = verification_failures
    # Deduplica também aliases cujo destino HTTP final é igual.
    merged = {}
    for op in opportunities:
        key = canonical_url(op.url)
        old = merged.get(key)
        if old is None or (op.official, op.score) > (old.official, old.score):
            merged[key] = op
    opportunities = sorted(merged.values(), key=lambda o: (-o.score, o.url))
    day = started.astimezone(ZoneInfo("America/Sao_Paulo")).date().isoformat()
    summary = daily_summary(opportunities, errors, day, len(health))
    # Um alerta pequeno por campanha. Falhas não marcam como enviado.
    if not dry_run:
        for op in opportunities:
            if actionable(op) and state.changed(op) and sent < max_alerts:
                try:
                    bot.send(opportunity_message(op))
                    state.mark(op)
                    sent += 1
                except Exception as exc:
                    errors.append(f"Entrega Telegram: {failure_reason(exc)}")
                    break
        if not state.summary_sent(day):
            try:
                bot.send(daily_summary(opportunities, errors, day, len(health)))
                state.mark_summary(day)
            except Exception as exc:
                errors.append(f"Resumo Telegram: {failure_reason(exc)}")
    result = {"started_at": started.isoformat(), "finished_at": utcnow().isoformat(),
              "dry_run": dry_run, "sent": sent, "sources": health, "errors": errors,
              "opportunities": [o.to_dict() for o in opportunities]}
    atomic_json(Path(report_dir) / "run.json", result)
    Path(report_dir, "summary.txt").write_text(summary, encoding="utf-8")
    for error in errors:
        LOG.warning("Falha registrada: %s", error)
    LOG.info("Concluído: %d campanhas, %d alertas, %d falhas", len(opportunities), sent, len(errors))
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
