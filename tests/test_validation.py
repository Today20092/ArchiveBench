from pathlib import Path

import pytest
import shutil

from archivebench.core import benchmark, run, save
from archivebench.report import public_result

from archivebench.validation import shortlist, validation_sections


def test_public_report_redacts_holdout_paths_and_internal_failure_paths():
    result = {
        "config": {
            "samples": [{"path": "C:/private/source.mov"}],
            "validation_samples": [{"path": "C:/private/source.mov"}],
        },
        "trials": [],
        "skipped": [{"reason": "Failed C:/private/run/validation-1/reference.mkv"}],
    }
    public = public_result(result)
    assert public["config"]["validation_samples"][0]["path"] == "[local source]"
    assert "C:/private" not in str(public)
    assert result["config"]["validation_samples"][0]["path"] == "C:/private/source.mov"


def test_fresh_sections_avoid_every_tuning_interval():
    samples = [
        {"path": "clip.mov", "start": 0, "seconds": 2},
        {"path": "clip.mov", "start": 8, "seconds": 2},
    ]
    sections = validation_sections(samples, {str(Path("clip.mov").resolve()): 20})
    assert sections[0]["start"] == 16
    assert sections[0]["seconds"] == 4
    with pytest.raises(ValueError, match="overlap"):
        validation_sections(
            samples,
            {str(Path("clip.mov").resolve()): 20},
            [{"path": "clip.mov", "start": 7, "seconds": 4}],
        )


def test_shortlist_keeps_smallest_and_fastest_and_rejects_missing_or_weak_scenes():
    result = {
        "config": {"samples": [{}, {}], "target_vmaf": 93},
        "samples": [
            {"id": "sample-1", "seconds": 1, "source_id": "one", "source_seconds": 100},
            {"id": "sample-2", "seconds": 1, "source_id": "two", "source_seconds": 10},
        ],
        "trials": [],
    }
    for encoder, quality, size, seconds, scores in [
        ("libx264", 18, 1, 10, [94, 95]),
        ("libx265", 18, 10, 1, [94, 95]),
        ("libx264", 20, 0.5, 0.5, [99, 92]),
        ("libx265", 20, 0.1, 0.1, [99]),
    ]:
        for index, score in enumerate(scores):
            result["trials"].append(
                {
                    "variant": "source",
                    "encoder": encoder,
                    "quality": quality,
                    "sample": f"sample-{index + 1}",
                    "bytes": size,
                    "encode_seconds": seconds,
                    "vmaf": score,
                }
            )
    assert [(c["encoder"], c["quality"]) for c in shortlist(result)] == [
        ("libx264", 18),
        ("libx265", 18),
    ]
    result["trials"] = result["trials"][:2]
    assert len(shortlist(result)) == 1


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg integration test")
def test_fixed_validation_and_resume_never_retune(tmp_path, monkeypatch):
    import archivebench.core as core

    source = tmp_path / "source.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=24",
            "-t",
            "4",
            "-c:v",
            "ffv1",
            str(source),
        ]
    )
    config = {
        "version": 1,
        "profile": "compact",
        "mode": "quick",
        "pixel_format": "yuv420p",
        "budget_minutes": 2,
        "target_vmaf": 80,
        "encoders": ["libx264"],
        "samples": [{"path": str(source), "start": 0, "seconds": 0.5}],
        "validation_samples": [{"path": str(source), "start": 2, "seconds": 1}],
    }
    config_path = tmp_path / "config.json"
    save(config_path, config)
    result = benchmark(config_path, tmp_path / "run")
    assert result["validation_required"] == 1
    assert result["validation_shortlist"]
    validation = [trial for trial in result["trials"] if trial["stage"] == "validation"]
    assert validation
    assert {(trial["encoder"], trial["quality"]) for trial in validation} == {
        (c["encoder"], c["quality"]) for c in result["validation_shortlist"]
    }

    def unexpected_measurement(*args, **kwargs):
        raise AssertionError("Resume retuned or repeated completed validation")

    monkeypatch.setattr(core, "score", unexpected_measurement)
    resumed = benchmark(config_path, tmp_path / "run")
    assert resumed["trials"] == result["trials"]
    assert resumed["validation_shortlist"] == result["validation_shortlist"]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg integration test")
def test_validation_timeout_resumes_frozen_settings_and_failed_holdout_cannot_tune(
    tmp_path, monkeypatch
):
    import subprocess
    import archivebench.core as core

    source = tmp_path / "source.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=160x90:rate=24",
            "-t",
            "4",
            "-c:v",
            "ffv1",
            str(source),
        ]
    )
    config = {
        "version": 1,
        "profile": "compact",
        "mode": "quick",
        "pixel_format": "yuv420p",
        "budget_minutes": 2,
        "target_vmaf": 93,
        "encoders": ["libx264"],
        "samples": [{"path": str(source), "start": 0, "seconds": 0.5}],
        "validation_samples": [{"path": str(source), "start": 2, "seconds": 1}],
    }
    config_path = tmp_path / "config.json"
    save(config_path, config)
    original_score = core.score

    def interrupt_holdout(*args, **kwargs):
        if "validation-" in str(args[5]):
            raise subprocess.TimeoutExpired("scoring", 1)
        return original_score(*args, **kwargs)

    monkeypatch.setattr(core, "score", interrupt_holdout)
    result = benchmark(config_path, tmp_path / "run")
    assert result["validation_status"] == "incomplete"

    def fail_holdout(*args, **kwargs):
        assert "validation-" in str(args[5]), "Holdout evidence triggered tuning"
        return {**original_score(*args, **kwargs), "vmaf": 1}

    monkeypatch.setattr(core, "score", fail_holdout)
    resumed = benchmark(config_path, tmp_path / "run")
    assert resumed["validation_status"] == "failed"
    assert [(c["encoder"], c["quality"]) for c in resumed["validation_shortlist"]] == [
        (c["encoder"], c["quality"]) for c in result["validation_shortlist"]
    ]
    assert [t for t in resumed["trials"] if t["stage"] == "tuning"] == result["trials"]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg integration test")
def test_tuning_budget_boundary_leaves_reserve_for_fixed_validation(tmp_path, monkeypatch):
    import archivebench.core as core

    source = tmp_path / "source.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=black:size=160x90:rate=24",
            "-t",
            "4",
            "-c:v",
            "ffv1",
            str(source),
        ]
    )
    config = {
        "version": 1,
        "profile": "compact",
        "mode": "quick",
        "pixel_format": "yuv420p",
        "budget_minutes": 2,
        "target_vmaf": 95,
        "encoders": ["libx264"],
        "samples": [{"path": str(source), "start": 0, "seconds": 0.5}],
        "validation_samples": [{"path": str(source), "start": 2, "seconds": 1}],
    }
    config_path = tmp_path / "config.json"
    save(config_path, config)
    original_score, original_clock = core.score, core.time.monotonic
    offset = [0.0]
    monkeypatch.setattr(core.time, "monotonic", lambda: original_clock() + offset[0])

    def scored(*args, **kwargs):
        measured = original_score(*args, **kwargs)
        if "sample-1" in str(args[5]) and "-screen" not in str(args[5]):
            offset[0] = 84
        return {**measured, "vmaf": 95}

    monkeypatch.setattr(core, "score", scored)
    result = benchmark(config_path, tmp_path / "run")
    assert result["validation_status"] == "validated"
    assert len([t for t in result["trials"] if t["stage"] == "tuning"]) == 1
    assert len([t for t in result["trials"] if t["stage"] == "validation"]) == 1
    assert 0 < result["remaining_seconds"] < 36
