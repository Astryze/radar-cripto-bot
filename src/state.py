"""Histórico versionado de observações, transições e entregas confirmadas."""
import json
from pathlib import Path

from .utils import atomic_json, canonical_url, digest, utcnow

LEGACY_KEYS = ("title", "cost", "reward", "reward_status", "reward_type", "deadline", "deadline_at",
               "eligibility", "kyc", "steps", "effort")
KEYS = LEGACY_KEYS + ("conclusion", "token", "token_quantity", "estimated_value", "withdrawability",
                      "starts_at", "countries", "participation_route")
KEYS += ("eligibility_requirements",)


def fingerprint(op, legacy=False):
    data = op.to_dict()
    return digest({k: data[k] for k in (LEGACY_KEYS if legacy else KEYS)})


def snapshot(op):
    data = op.to_dict()
    return {k: data[k] for k in dict.fromkeys(KEYS + ("url", "project", "source_id", "official", "score", "priority"))}


class State:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {"version": 2, "sent": {}, "summaries": [], "campaigns": {},
                     "source_health": {}, "cooldowns": {}, "pending_sources": {}}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if (data.get("version") not in (1, 2) or not isinstance(data.get("sent"), dict)
                    or not isinstance(data.get("summaries"), list)):
                raise ValueError("Estado inválido; não reiniciar deduplicação silenciosamente")
            self.data.update(data)
            self.data["version"] = 2
            for key in ("campaigns", "source_health", "cooldowns", "pending_sources"):
                if not isinstance(self.data[key], dict):
                    raise ValueError("Histórico inválido")

    def changed(self, op):
        sent = self.data["sent"].get(canonical_url(op.url))
        return sent not in {fingerprint(op), fingerprint(op, legacy=True)}

    def event(self, op):
        from .scoring import actionable
        key = canonical_url(op.url)
        record = self.data["campaigns"].get(key)
        if not self.changed(op):
            return None
        prior = record.get("latest", {}) if record else {}
        if prior and op.deadline == "encerrado" and prior.get("deadline") != "encerrado":
            return "campanha encerrada"
        if actionable(op):
            if prior and prior.get("cost") not in {"GRATUITA CONFIRMADA"}:
                return "gratuidade confirmada após investigação"
            return (record or {}).get("pending_event") or ("oportunidade atualizada" if prior else "nova oportunidade gratuita")
        if record and record.get("pending_event") == "campanha encerrada" and op.deadline == "encerrado":
            return "campanha encerrada"
        if record and record.get("notified") and fingerprint(op) != record.get("notified_hash"):
            return "regras ou disponibilidade alteradas"
        return None

    def observe(self, op, event=None):
        key = canonical_url(op.url)
        record = self.data["campaigns"].setdefault(key, {"first_seen": utcnow().isoformat()})
        record.update(latest=snapshot(op), last_seen=utcnow().isoformat(), pending_event=event)

    def mark(self, op):
        key = canonical_url(op.url)
        self.data["sent"][key] = fingerprint(op)
        if key not in self.data["campaigns"]:
            self.observe(op)
        self.data["campaigns"][key].update(notified=snapshot(op), notified_hash=fingerprint(op), pending_event=None)
        self.save()

    def summary_sent(self, day):
        # Preserva o resumo antigo v1, mas permite um único relatório de migração v2.
        return f"v2:{day}" in self.data["summaries"]

    def mark_summary(self, day):
        self.data["summaries"] = (self.data["summaries"] + [f"v2:{day}"])[-120:]
        self.save()

    def save(self):
        atomic_json(self.path, self.data)
