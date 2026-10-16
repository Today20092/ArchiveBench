import json
import shutil
import subprocess
import time

import pytest

from archivebench.budget import deadline
from archivebench.core import benchmark, digest, run, save
from archivebench.experiments import experiment_plan
from archivebench.fixed import frontier, work_items


def config(source):
    return {
        "version": 1,
        "profile": "editing",
        "mode": "quick",
        "strategy": "fixed",
        "budget_minutes": 2,
        "pixel_format": "source",
        "resolution": "original",
        "samples": [{"path": str(source), "start": 0, "seconds": 1}],
        "encoders": ["libx264"],
        "fixed_settings": {"libx264": [23, 29]},
    }


def test_fixed_plan_and_round_robin():
    c = config("source")
    c["encoders"] = ["libx264", "hevc_nvenc"]
    assert experiment_plan(c)["bounds"]["measured_encodes"] == 4
    assert [w["encoder"] for w in work_items(c)] == ["libx264", "hevc_nvenc"] * 2
    c["fixed_settings"] = {"libx264": [23, 23]}
    with pytest.raises(ValueError):
        experiment_plan(c)


def test_deadline_bounds_hash_and_command(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"test")
    token = deadline.set(time.monotonic() - 1)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            digest(source)
        with pytest.raises(subprocess.TimeoutExpired):
            run(["not-started"])
    finally:
        deadline.reset(token)


def test_frontier_does_not_mix_formats():
    a = {
        "variant": "source",
        "sample": "sample-1",
        "encoder": "libx265",
        "quality": 24,
        "bytes": 100,
        "encode_seconds": 5,
        "vmaf": 95,
    }
    b = {**a, "variant": "420", "bytes": 80, "encode_seconds": 3}
    assert len(frontier([a, b])) == 2


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_fixed_real_encode_resume_review_and_budget(tmp_path):
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
            "3",
            "-c:v",
            "ffv1",
            str(source),
        ]
    )
    c = config(source)
    path = tmp_path / "config.json"
    save(path, c)
    output = tmp_path / "run"
    r = benchmark(path, output)
    assert r["status"] == "completed"
    assert {t["quality"] for t in r["trials"]} == {23, 29}
    assert len(r["trials"]) == 2
    assert not r["screening"] and "tuning_searches" not in r
    assert all(t["scoring_seconds"] > 0 for t in r["trials"])
    assert "measured starting" in r["validation_status"]
    assert (output / "report.html").is_file()
    assert all("review_media" not in t for t in r["trials"])
    from archivebench.review import prepare_review

    reviewed = prepare_review(output, r["trials"][0]["id"], 60)
    assert reviewed["media"] == "available"
    prepared = json.loads((output / "results.json").read_text())
    assert "review_media" not in prepared["trials"][1]
    assert prepared["trials"][0]["sha256"] == r["trials"][0]["sha256"]
    before = [(t["sha256"], t["encode_seconds"]) for t in r["trials"]]
    r = benchmark(path, output)
    assert [(t["sha256"], t["encode_seconds"]) for t in r["trials"]] == before
    original = (output / "results.json").read_bytes()
    c["fixed_settings"]["libx264"] = [24]
    save(path, c)
    with pytest.raises(ValueError, match="Config changed"):
        benchmark(path, output)
    assert (output / "results.json").read_bytes() == original
    c["budget_minutes"] = 0.00001
    save(path, c)
    short = benchmark(path, tmp_path / "short")
    assert short["status"] == "budget_exhausted"
    assert not short["trials"]
    assert all(w["status"] == "pending" for w in short["work"])
    assert (
        json.loads((tmp_path / "short" / "progress.json").read_text())["status"]
        == "budget_exhausted"
    )
