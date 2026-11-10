from pathlib import Path

import yaml

from src.feed_reader import load_sources


def test_config_and_workflow():
    sources = load_sources(Path("config/sources.json"))
    assert sources[0].id == "bitdegree"
    files = [Path(".github/workflows/radar.yml")]
    assert files[0].is_file()
    # MediaFlow may add a separate workflow without changing Radar behavior.
    # BaseLoader evita a interpretação YAML 1.1 de `on` como booleano.
    config = yaml.load(files[0].read_text(), Loader=yaml.BaseLoader)
    assert config["on"]["schedule"][0]["cron"] == "15 13 * * *"
    assert "workflow_dispatch" in config["on"]
    assert config["jobs"]["radar"]["concurrency"]["cancel-in-progress"] == "false"
    assert "secrets.TELEGRAM_BOT_TOKEN" in files[0].read_text()
    assert config["jobs"]["radar"]["needs"] == "validate"
