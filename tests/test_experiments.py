import json
import sys
import shutil

import pytest

from archivebench.cli import main
from archivebench.core import run


def test_initial_plan_is_bounded_and_discloses_choices(tmp_path, monkeypatch, capsys):
    source = tmp_path / "clip.mov"
    source.touch()
    config = {
        "version": 1,
        "profile": "editing",
        "mode": "quick",
        "comparison": "initial",
        "budget_minutes": 15,
        "pixel_format": "source",
        "resolution": "original",
        "samples": [{"path": str(source), "start": 0, "seconds": 2}],
        "encoders": ["libx265", "hevc_nvenc"],
        "target_vmafs": [80, 90, 95, 97],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setattr(sys, "argv", ["archivebench", "plan", str(path)])
    main()
    plan = json.loads(capsys.readouterr().out)
    assert plan["bounds"]["tuning_attempts"] == 12
    assert plan["bounds"]["screens"] == 2
    assert plan["encode_repeats"] == 1
    assert plan["encoders"][0]["encoder"] == "libx265"
    assert "-crf" in plan["encoders"][0]["controls"]
    assert plan["estimate"]["seconds"] is None
    config["samples"] *= 3
    path.write_text(json.dumps(config))
    with pytest.raises(SystemExit):
        main()
    assert "comprehensive" in capsys.readouterr().err
    config.pop("comparison")
    path.write_text(json.dumps(config))
    main()
    assert json.loads(capsys.readouterr().out)["bounds"]["tuning_attempts"] == 144


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_initial_run_caps_attempts_and_reports_stages_and_resume(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=128x72:rate=6",
            "-t",
            "4",
            "-c:v",
            "ffv1",
            str(source),
        ]
    )
    config = {
        "version": 1,
        "profile": "editing",
        "mode": "quick",
        "comparison": "initial",
        "initial_trial_limit": 1,
        "budget_minutes": 2,
        "pixel_format": "source",
        "resolution": "original",
        "samples": [{"path": str(source), "start": 0, "seconds": 1}],
        "validation_samples": [{"path": str(source), "start": 2, "seconds": 1}],
        "encoders": ["libx264", "hevc_nvenc"],
        "target_vmafs": [80, 90, 95, 97],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    output = tmp_path / "results"
    monkeypatch.setattr(
        sys, "argv", ["archivebench", "benchmark", str(path), "--output", str(output)]
    )
    main()
    result = json.loads((output / "results.json").read_text())
    assert result["initial_attempts"] == 1
    assert len([t for t in result["trials"] if t["stage"] == "tuning"]) == 1
    assert result["comparison_limit_reached"] is True
    before = [(t["id"], t["sha256"]) for t in result["trials"]]
    progress = json.loads((output / "progress.json").read_text())
    assert {"hashing", "reference", "screen", "pilot", "encode", "scoring", "validation"} <= set(
        progress["stages_seen"]
    )
    assert progress["completed_trials"] == len(before)
    assert progress["completed_screens"] + progress["failed_screens"] == 2
    assert progress["pilot_estimate"]["seconds"] > 0
    assert "approximate" in progress["pilot_estimate"]["note"]
    assert progress["remaining_work"] == "adaptive; exact count unknown"
    main()
    resumed = json.loads((output / "results.json").read_text())
    assert resumed["initial_attempts"] == 1
    assert [(t["id"], t["sha256"]) for t in resumed["trials"]] == before
    monkeypatch.setattr(sys, "argv", ["archivebench", "status", str(output)])
    main()
    assert "completed_trials" in capsys.readouterr().out
    config["budget_minutes"] = 0.000001
    path.write_text(json.dumps(config))
    exhausted = tmp_path / "exhausted"
    monkeypatch.setattr(
        sys, "argv", ["archivebench", "benchmark", str(path), "--output", str(exhausted)]
    )
    main()
    assert json.loads((exhausted / "progress.json").read_text())["status"] == "budget_exhausted"
