"""Persiste deduplicação numa branch separada, usando apenas GITHUB_TOKEN do checkout.

Sem cache descartável e sem commit de credenciais/relatórios/conteúdo coletado.
"""
import argparse
import subprocess
from pathlib import Path

BRANCH = "radar-state"
STATE = Path("state/radar.json")
PARENT = Path("state/parent-sha")


def git(*args, input=None, check=True):
    return subprocess.run(["git", *args], input=input, text=True,
                          capture_output=True, check=check)


def restore():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    remote = git("ls-remote", "--exit-code", "--heads", "origin", BRANCH, check=False)
    if remote.returncode == 2:
        if STATE.exists():
            raise RuntimeError("Estado local inesperado sem branch remota")
        PARENT.write_text("")
        return
    if remote.returncode != 0:
        raise RuntimeError("Não foi possível consultar estado remoto; não zerar histórico")
    git("fetch", "--depth=1", "origin", f"refs/heads/{BRANCH}")
    parent = git("rev-parse", "FETCH_HEAD").stdout.strip()
    contents = git("show", f"{parent}:radar.json").stdout
    from src.state import State
    temp = STATE.with_suffix(".restore")
    temp.write_text(contents, encoding="utf-8")
    State(temp)  # Rejeita corrupção antes de substituir estado.
    temp.replace(STATE)
    PARENT.write_text(parent)


def save():
    if not STATE.exists():
        return
    if not PARENT.exists():
        raise RuntimeError("Restauração não executada; não sobrescrever estado")
    parent = PARENT.read_text().strip()
    content = STATE.read_text(encoding="utf-8")
    if parent and git("show", f"{parent}:radar.json").stdout == content:
        return
    blob = git("hash-object", "-w", "--stdin", input=content).stdout.strip()
    tree = git("mktree", input=f"100644 blob {blob}\tradar.json\n").stdout.strip()
    args = ["-c", "user.name=github-actions[bot]", "-c",
            "user.email=41898282+github-actions[bot]@users.noreply.github.com", "commit-tree", tree]
    if parent:
        args.extend(["-p", parent])
    commit = git(*args, input="Persist Radar Cripto delivery state\n").stdout.strip()
    # Fast-forward somente; sem force. Conflitos deixam o job vermelho.
    git("push", "origin", f"{commit}:refs/heads/{BRANCH}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["restore", "save"])
    args = parser.parse_args()
    try:
        {"restore": restore, "save": save}[args.action]()
    except Exception:
        # subprocess stderr pode conter URLs autenticadas; não registrar.
        print("Falha ao sincronizar estado; consulte permissão contents:write e branch radar-state.", file=sys.stderr)
        sys.exit(1)
