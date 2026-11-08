"""Testes offline do bloqueio; não usam conta, cookies ou storage_state."""
import json
from pathlib import Path
import pytest
from src.bitdegree_access_policy import require_authorized_access
from src.bitdegree_authenticated import blocked_report, main
from scripts.bitdegree_login import main as login


def test_login_stops_before_browser_or_session(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert login() == 2
    assert not (tmp_path / '.auth').exists()
    assert 'não habilitados' in capsys.readouterr().out


def test_no_policy_override():
    with pytest.raises(PermissionError):
        require_authorized_access()


def test_each_mission_marked_not_collected():
    missions = json.loads(Path('config/bitdegree_diagnostic_missions.json').read_text())
    report = blocked_report(missions)
    assert len(report['missions']) == 6
    assert not report['session_loaded'] and not report['chromium_started']
    assert all(m['questions_found'] is None and m['http_status'] is None for m in report['missions'])
    assert report['telegram_sent'] == 0


@pytest.mark.parametrize('secret', [None, 'EXEMPLO_ARTIFICIAL_NAO_E_SESSAO'])
def test_missing_or_supplied_secret_not_read(secret, tmp_path, monkeypatch, capsys):
    if secret:
        monkeypatch.setenv('BITDEGREE_STORAGE_STATE_B64', secret)
    else:
        monkeypatch.delenv('BITDEGREE_STORAGE_STATE_B64', raising=False)
    monkeypatch.setattr('sys.argv', ['authenticated', '--reports', str(tmp_path)])
    assert main() == 0
    data = (tmp_path / 'bitdegree-authenticated.json').read_text()
    assert 'EXEMPLO_ARTIFICIAL' not in data + capsys.readouterr().out
    assert not json.loads(data)['session_loaded']


def test_session_directory_ignored():
    assert '.auth/' in Path('.gitignore').read_text().splitlines()


def test_workflow_no_session_secret_or_browser_install():
    workflow = Path('.github/workflows/radar.yml').read_text()
    assert 'src.bitdegree_authenticated' in workflow
    assert 'BITDEGREE_STORAGE_STATE_B64' not in workflow
