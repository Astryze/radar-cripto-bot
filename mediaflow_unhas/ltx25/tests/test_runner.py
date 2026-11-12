"""Tests are CPU-only: no model weights, no paid service and no fake output."""
import json
from pathlib import Path
import pytest
from PIL import Image
from mediaflow_unhas.ltx25 import runner


def test_official_cli_has_reference_binding():
    cmd = runner.build_command(
        Path("/photos/ref.png"), Path("/out/demo.mp4"), Path("/models")
    )
    assert cmd[:4] == ["uv", "run", "python", "-m"]
    assert "ltx_pipelines.distilled" in cmd
    idx = cmd.index("--image")
    assert cmd[idx + 1:idx + 5] == ["/photos/ref.png", "0", "1.0", "replace"]
    assert cmd[cmd.index("--num-frames") + 1] == "121"
    assert cmd[cmd.index("--width") + 1] == "576"
    assert cmd[cmd.index("--height") + 1] == "1024"
    assert any("gemma4" in x for x in cmd)
    assert any("vae" in x for x in cmd)


def test_reject_wrong_geometry():
    with pytest.raises(ValueError, match="9:16"):
        runner.build_command("ref.png", "out.mp4", "models", width=720, height=1280)


def test_refuse_tiny_images(tmp_path):
    image = tmp_path / "tiny.png"
    Image.new("RGB", (120, 120), "red").save(image)
    with pytest.raises(ValueError, match="512"):
        runner.validate_image(image)


def test_cpu_plan_no_video_generated(tmp_path, monkeypatch, capsys):
    inp = tmp_path / "input.png"
    Image.new("RGB", (576, 1024), (13, 63, 56)).save(inp)
    monkeypatch.setattr(runner, "gpu_check", lambda: (False, "CPU sem CUDA"))
    out = tmp_path / "out"
    rc = runner.main(["--image", str(inp), "--outdir", str(out)])
    assert rc == 0
    plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    assert plan["planned_only"]
    assert not plan["ready_gpu"]
    assert not (out/"nail_cat_eye_emerald_ltx25.mp4").exists()
    assert "DRY_RUN_ONLY" in capsys.readouterr().out


def test_actual_model_run_refuses_no_gpu(tmp_path, monkeypatch):
    inp = tmp_path / "input.png"
    Image.new("RGB", (576, 1024), "green").save(inp)
    monkeypatch.setattr(runner, "gpu_check", lambda: (False, "CPU sem CUDA"))
    with pytest.raises(RuntimeError, match="CPU sem CUDA"):
        runner.main(["--image", str(inp), "--outdir", str(tmp_path/"out"), "--run"])


def test_models_missing_fail_closed(tmp_path):
    with pytest.raises(FileNotFoundError, match="Pesos não instalados"):
        runner.check_models(tmp_path)
