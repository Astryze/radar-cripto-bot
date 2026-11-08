"""Estado mínimo; só grava alertas depois que o Telegram confirma a entrega."""
import json
from pathlib import Path

from .utils import atomic_json, canonical_url, digest


def fingerprint(op):
    # Trechos/publicação não mudam o alerta; custo, regras e prazo mudam.
    keys = ("title", "cost", "reward", "reward_status", "reward_type", "deadline", "deadline_at",
            "eligibility", "kyc", "steps", "effort")
    data = op.to_dict()
    return digest({k: data[k] for k in keys})


class State:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {"version": 1, "sent": {}, "summaries": []}
        if self.path.exists():
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if (data.get("version") != 1 or not isinstance(data.get("sent"), dict)
                    or not isinstance(data.get("summaries"), list)):
                raise ValueError("Estado inválido; não reiniciar deduplicação silenciosamente")
            self.data = data

    def changed(self, op):
        return self.data["sent"].get(canonical_url(op.url)) != fingerprint(op)

    def mark(self, op):
        self.data["sent"][canonical_url(op.url)] = fingerprint(op)
        self.save()

    def summary_sent(self, day):
        return day in self.data["summaries"]

    def mark_summary(self, day):
        self.data["summaries"] = (self.data["summaries"] + [day])[-60:]
        self.save()

    def save(self):
        atomic_json(self.path, self.data)
