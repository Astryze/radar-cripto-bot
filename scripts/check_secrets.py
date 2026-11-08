"""Varredura offline; relata caminhos e tipo, nunca o segredo."""
import re
import sys
import zipfile
from pathlib import Path

PATTERNS = {
    "Telegram token": re.compile(rb"\b[0-9]{6,15}:[A-Za-z0-9_-]{30,}\b"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "Private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}
EXCLUDED = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", "logs", "reports", "state"}


def scan(root):
    findings = []
    for path in Path(root).rglob("*"):
        if not path.is_file() or any(p in EXCLUDED for p in path.parts):
            continue
        items = [(str(path), path.read_bytes())]
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as archive:
                items.extend((f"{path}!{name}", archive.read(name)) for name in archive.namelist()
                             if not name.endswith("/"))
        for name, content in items:
            for kind, pattern in PATTERNS.items():
                if pattern.search(content):
                    findings.append((name, kind))
    return findings


if __name__ == "__main__":
    findings = scan(Path(__file__).resolve().parents[1])
    for name, kind in findings:
        print(f"Credencial possível: {kind} em {name}")
    if not findings:
        print("Nenhuma credencial reconhecida no código ou ZIP original.")
    sys.exit(bool(findings))
