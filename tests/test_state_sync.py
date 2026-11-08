import subprocess
from pathlib import Path

from scripts.state_sync import restore, save
from src.state import State


def command(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True)


def test_git_state_round_trip_without_remote_service(tmp_path, monkeypatch):
    remote = tmp_path / "remote.git"
    command("git", "init", "--bare", str(remote))
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    command("git", "init", "-b", "main")
    command("git", "config", "user.name", "Test")
    command("git", "config", "user.email", "test@example.org")
    Path("README.md").write_text("test")
    command("git", "add", "README.md")
    command("git", "commit", "-m", "test")
    command("git", "remote", "add", "origin", str(remote))
    command("git", "push", "origin", "main")
    restore()
    state = State("state/radar.json")
    state.data["sent"] = {"https://example.org/quest": "fingerprint"}
    state.save()
    save()
    Path("state/radar.json").unlink()
    restore()
    restored = State("state/radar.json")
    assert restored.data == state.data
    main = command("git", "rev-parse", "HEAD").stdout
    before = command("git", "ls-remote", "origin", "radar-state").stdout
    save()  # Nenhum commit novo se nada foi enviado.
    assert command("git", "ls-remote", "origin", "radar-state").stdout == before
    assert command("git", "rev-parse", "HEAD").stdout == main
