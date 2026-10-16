import json
import shutil
import subprocess
from pathlib import Path

import pytest

from archivebench.jobs import create_job, inspect_job, run_job
from archivebench.core import run


def settings():
    return {
        "version": 2,
        "type": "archive-settings",
        "encoder": "libx264",
        "quality": 30,
        "pixel_format": "source",
        "resolution": "original",
        "minimum_saving": 0.1,
    }


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_job_preflight_rejects_silent_pixel_format_substitution(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=24",
            "-t",
            "0.5",
            "-c:v",
            "ffv1",
            "-pix_fmt",
            "yuv422p10le",
            str(source / "clip.mkv"),
        ]
    )
    preset = tmp_path / "preset.json"
    preset.write_text(json.dumps({**settings(), "encoder": "libsvtav1"}))
    plan = inspect_job(create_job(source, tmp_path / "output", preset))
    assert plan["files"][0]["compatibility"] == "unsupported"
    assert "bit depth/chroma" in str(plan["files"][0]["gaps"])


def test_job_snapshot_and_exception_boundaries(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    (source / "keep.mov").write_bytes(b"original")
    preset = tmp_path / "preset.json"
    preset.write_text(json.dumps(settings()))
    job = create_job(
        source, tmp_path / "output", preset, [{"path": "keep.mov", "action": "keep-original"}]
    )
    preset.write_text("{}")
    result = inspect_job(job)
    assert result["files"][0]["action"] == "keep-original"
    assert result["files"][0]["output"] is None
    assert result["files"][0]["settings"] is None
    assert result["estimates"]["status"] == "unknown"
    with pytest.raises(ValueError, match="relative"):
        create_job(
            source, tmp_path / "out", preset, [{"path": "../other.mov", "action": "keep-original"}]
        )


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_two_projects_resume_and_changed_media(tmp_path, monkeypatch):
    preset = tmp_path / "preset.json"
    preset.write_text(json.dumps(settings()))
    for name in ("first", "second"):
        source = tmp_path / name
        source.mkdir()
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=64x64:rate=10",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440",
                "-t",
                "1",
                "-c:v",
                "mpeg2video",
                "-b:v",
                "8M",
                "-c:a",
                "pcm_s16le",
                str(source / "clip.mkv"),
            ]
        )
        (source / "keep.mov").write_bytes(b"keep")
        stronger = {**settings(), "quality": 28}
        job = create_job(
            source,
            tmp_path / (name + "-out"),
            preset,
            [
                {"path": "keep.mov", "action": "keep-original"},
                {"path": "clip.mkv", "action": "stronger-setting", "preset": stronger},
            ],
        )
        config = tmp_path / (name + ".json")
        config.write_text(json.dumps(job))
        plan = run_job(config)
        assert plan["files"][0]["settings"]["quality"] == 28
        assert plan["files"][0]["footage_scope"] == "untested"
        assert plan["files"][0]["sample_check"] == "recommended"
        if name == "first":
            execute_process = subprocess.Popen

            def interrupt_encode(args, **kwargs):
                if str(args[-1]).endswith(".partial.mkv"):
                    raise KeyboardInterrupt
                return execute_process(args, **kwargs)

            with monkeypatch.context() as interrupted:
                interrupted.setattr(subprocess, "Popen", interrupt_encode)
                with pytest.raises(KeyboardInterrupt):
                    run_job(config, True)
            interrupted_manifest = json.loads(
                (Path(job["output_root"]) / "archive-manifest.json").read_text()
            )
            assert interrupted_manifest["records"][0]["status"] == "pending"
            summary = (Path(job["output_root"]) / "archive-summary.html").read_text()
            assert "Last run: interrupted" in summary
            assert "Unfinished: 2" in summary
            assert "archive-job.json" in summary
            assert not (Path(job["output_root"]) / ".lock").exists()
        run_job(config, True)
        manifest_path = Path(job["output_root"]) / "archive-manifest.json"
        manifest = json.loads(manifest_path.read_text())
        assert {row["status"] for row in manifest["records"]} == {"verified", "keep_original"}
        summary = (Path(job["output_root"]) / "archive-summary.html").read_text()
        assert "Unfinished: 0" in summary
        assert "Verified: 1" in summary and "Kept original: 1" in summary
        assert "Net storage reclaimed after cleanup: 0 bytes" in summary
        archived = Path(manifest["records"][0]["output"])
        before = archived.stat().st_mtime_ns
        preset.write_text("{}")
        run_job(config, True)
        assert archived.stat().st_mtime_ns == before
        archived.write_bytes(b"changed")
        with pytest.raises(ValueError, match="changed/missing"):
            run_job(config, True)
        changed_job = {**job, "exceptions": [{"path": "keep.mov", "action": "keep-original"}]}
        config.write_text(json.dumps(changed_job))
        with pytest.raises(ValueError, match="another source/settings"):
            run_job(config, True)
        preset.write_text(json.dumps(settings()))


def test_preflight_preserves_unsupported_files(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    (source / "broken.mov").write_bytes(b"invalid media")
    preset = tmp_path / "preset.json"
    preset.write_text(json.dumps(settings()))
    job = create_job(source, tmp_path / "output", preset)
    plan = inspect_job(job)
    assert plan["files"][0]["action"] == "keep-original"
    assert plan["files"][0]["compatibility"] == "unsupported"
    assert plan["files"][0]["gaps"]
    assert not (tmp_path / "output").exists()


def test_preflight_operational_error_is_not_format_incompatibility(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    (source / "clip.mov").write_bytes(b"original")
    preset = tmp_path / "preset.json"
    preset.write_text(json.dumps(settings()))
    job = create_job(source, tmp_path / "output", preset)
    with pytest.raises(OSError):
        inspect_job(job, ffprobe=str(tmp_path / "missing-ffprobe.exe"))


@pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("node"), reason="FFmpeg and Node required"
)
def test_report_export_rates_and_scope_reach_job_preflight(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=10",
            "-t",
            "1",
            "-c:v",
            "ffv1",
            str(source / "clip.mkv"),
        ]
    )
    result = {
        "identity": "benchmark",
        "config": {"samples": [{}], "pixel_format": "source"},
        "samples": [
            {"id": "sample-1", "seconds": 1, "video": {"width": 32, "height": 32, "fps": "10"}}
        ],
        "trials": [
            {
                "id": "trial",
                "sample": "sample-1",
                "encoder": "libx264",
                "quality": 30,
                "pixel_format": "yuv420p",
                "bytes": 1000,
                "encode_seconds": 2,
                "vmaf": 90,
                "ssim": 0.99,
                "preset_encoder_options": [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "medium",
                    "-crf",
                    "30",
                    "-pix_fmt",
                    "yuv420p",
                ],
            }
        ],
    }
    script = "import {archivePreset} from './report/math.js'; const r=JSON.parse(process.argv[1]); console.log(JSON.stringify(archivePreset(r,r.trials[0])));"
    preset = tmp_path / "preset.json"
    exported = subprocess.run(
        ["node", "--input-type=module", "-e", script, json.dumps(result)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    preset.write_text(exported)
    row = inspect_job(create_job(source, tmp_path / "output", preset))["files"][0]
    assert row["footage_scope"] == "untested"
    assert row["sample_check"] == "recommended"
    assert row["estimates"]["video_bytes"] == 1000
    assert row["estimates"]["encode_seconds"] == 2
    assert json.loads(preset.read_text())["scope"]["footage"][0]["width"] == 32
    result["samples"][0]["video"] = {"width": 64, "height": 64, "fps": "10"}
    exported = subprocess.run(
        ["node", "--input-type=module", "-e", script, json.dumps(result)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    preset.write_text(exported)
    row = inspect_job(create_job(source, tmp_path / "output", preset))["files"][0]
    assert row["footage_scope"] == "matches historical scope"


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_unhelpful_archive_is_recorded_and_original_retained(tmp_path):
    source = tmp_path / "project"
    source.mkdir()
    clip = source / "tiny.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=10",
            "-t",
            "1",
            "-c:v",
            "libx264",
            "-crf",
            "40",
            str(clip),
        ]
    )
    preset = tmp_path / "preset.json"
    preset.write_text(json.dumps({**settings(), "quality": 12}))
    job = create_job(source, tmp_path / "output", preset)
    config = tmp_path / "job.json"
    config.write_text(json.dumps(job))
    run_job(config, True)
    record = json.loads((tmp_path / "output/archive-manifest.json").read_text())["records"][0]
    assert record["status"] == "not_worth_encoding"
    assert clip.exists()
    assert not Path(record["output"]).exists()
    clip.write_bytes(b"changed source")
    with pytest.raises(ValueError, match="Original changed"):
        run_job(config, True)
