import json
import shutil
from pathlib import Path

import pytest

from archivebench.core import run, save, probe
from archivebench.desktop import project_defaults, selected_job
from archivebench.jobs import inspect_job, run_job
from archivebench.mux import timecode, validate_mux


def test_project_selection(tmp_path):
    original = tmp_path / "Original Footage"
    original.mkdir()
    (original / "a.mov").touch()
    (tmp_path / "b.mp4").touch()
    (tmp_path / "proxies").mkdir()
    (tmp_path / "proxies" / "a.mov").touch()
    output, rows = project_defaults(tmp_path)
    assert output == tmp_path / "Archived Footage"
    assert [(p.name, selected) for p, selected in rows] == [("b.mp4", False), ("a.mov", True)]
    assert project_defaults(original)[0] == output
    with pytest.raises(ValueError):
        validate_mux({"container": "mkv", "timecode_mode": "preserve"})


def test_desktop_build_and_cancel(tmp_path):
    from archivebench.desktop import window
    from archivebench.presets import make_preset

    source = tmp_path / "project"
    source.mkdir()
    library = tmp_path / "presets"
    library.mkdir()
    save(
        library / "preset.json",
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 24,
                "pixel_format": "source",
            }
        ),
    )
    form, result = window(source, library)
    form.withdraw()
    form.update_idletasks()
    form.destroy()
    assert result == {}
    assert not list(source.glob("*.json"))


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize(
    "container,audio,encoder,pixel",
    [
        ("mov", "copy", "libx265", "source"),
        ("mp4", "aac", "libsvtav1", "yuv420p10le"),
        ("mov", "copy", "hevc_nvenc", "yuv420p10le"),
    ],
)
def test_camera_container_selection_resume(
    tmp_path: Path, container, audio, encoder, pixel, monkeypatch
):
    if encoder.endswith("_nvenc") and not shutil.which("nvidia-smi"):
        pytest.skip("NVIDIA device required for this adapter check")
    root = tmp_path / "Original Footage"
    root.mkdir()
    source = root / "camera.mov"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=25",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "1",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map",
            "1:a",
            "-map",
            "1:a",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-crf",
            "0",
            "-color_range",
            "tv",
            "-pix_fmt",
            "yuv422p10le",
            "-c:a",
            "pcm_s16le",
            "-timecode",
            "01:02:03:00",
            str(source),
        ]
    )
    shutil.copyfile(source, root / "unselected.mov")
    preset = tmp_path / "preset.json"
    save(
        preset,
        {
            "version": 2,
            "type": "archive-settings",
            "encoder": encoder,
            "quality": 24,
            "pixel_format": pixel,
            "resolution": "original",
        },
    )
    job = selected_job(
        root,
        tmp_path / "Archived Footage",
        preset,
        ["camera.mov"],
        {"container": container, "audio_mode": audio, "timecode_mode": "preserve"},
    )
    job["progress"] = False
    job["continue_on_error"] = False
    plan = inspect_job(job)
    assert len(plan["files"]) == 1
    assert plan["files"][0]["action"] == "encode", plan["files"][0]["gaps"]
    path = tmp_path / "job.json"
    save(path, job)
    run_job(path, True)
    manifest = Path(job["output_root"]) / "archive-manifest.json"
    result = json.loads(manifest.read_text())
    assert result["records"][0]["status"] == "verified"
    output = Path(result["records"][0]["output"])
    assert output.suffix == "." + container
    assert timecode(probe(output)) == timecode(probe(source))
    assert sum(s["codec_type"] == "audio" for s in probe(output)["streams"]) == 4
    before = output.stat().st_mtime_ns
    run_job(path, True)
    assert output.stat().st_mtime_ns == before
    assert source.exists() and (root / "unselected.mov").exists()
    if container == "mov":
        import importlib

        engine = importlib.import_module("archivebench.archive")
        failed_job = selected_job(
            root,
            tmp_path / "continued",
            preset,
            ["camera.mov", "unselected.mov"],
            {"container": "mov", "audio_mode": "copy", "timecode_mode": "preserve"},
        )
        failed_job["progress"] = False
        failed_path = tmp_path / "continued.json"
        save(failed_path, failed_job)
        original_run = engine.run

        def fail_one(args, timeout=120):
            if str(args[-1]).endswith("camera.mov.archive.mov.partial.mov"):
                raise RuntimeError("simulated individual encode failure")
            return original_run(args, timeout)

        monkeypatch.setattr(engine, "run", fail_one)
        run_job(failed_path, True)
        records = json.loads((tmp_path / "continued" / "archive-manifest.json").read_text())[
            "records"
        ]
        assert [r["status"] for r in records] == ["failed", "verified"]
        assert source.exists()
        from archivebench.acceptance import record_acceptance
        from archivebench.archive import cleanup

        dest = tmp_path / "continued"
        record_acceptance(
            dest, "visual", "accept", "synthetic-test", note="Synthetic test attestation only"
        )
        record_acceptance(
            dest,
            "editor",
            "accept",
            "synthetic-test",
            editor="test fixture",
            project_copy="synthetic-only",
            note="Synthetic test attestation only",
        )
        with pytest.raises(ValueError, match="Select only"):
            cleanup(dest, True, True, selected_sources=[str(source)])
        cleanup(dest, True, True, selected_sources=[str(root / "unselected.mov")])
        assert source.exists() and not (root / "unselected.mov").exists()
