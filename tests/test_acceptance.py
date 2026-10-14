import json
from pathlib import Path

import pytest

from archivebench.acceptance import inspect_acceptance, record_acceptance
from archivebench.archive import cleanup
from archivebench.core import run
from archivebench.jobs import create_job, run_job


def completed_job(tmp_path, count=1):
    source = tmp_path / "source"
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
    preset = tmp_path / "preset.json"
    if count == 2:
        (source / "second.mkv").write_bytes((source / "clip.mkv").read_bytes())
    preset.write_text(
        json.dumps(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 30,
                "pixel_format": "source",
                "resolution": "original",
                "minimum_saving": 0.1,
            }
        )
    )
    output = tmp_path / "output"
    config = tmp_path / "job.json"
    config.write_text(json.dumps(create_job(source, output, preset)))
    run_job(config, True)
    return source, output


def test_replacement_requires_separate_bound_visual_and_editor_acceptance(tmp_path):
    source, output = completed_job(tmp_path)
    assert inspect_acceptance(output)["eligible"] == []
    with pytest.raises(ValueError, match="acceptance"):
        cleanup(output, True, True)
    assert (source / "clip.mkv").exists()
    record_acceptance(output, "visual", "accept", "Test user", note="Reviewed picture and audio")
    assert inspect_acceptance(output)["eligible"] == []
    record_acceptance(
        output,
        "editor",
        "accept",
        "Test user",
        editor="Test NLE 1",
        project_copy="project-copy",
        note="Reopened and checked timeline/audio",
    )
    state = inspect_acceptance(output)
    assert len(state["eligible"]) == 1
    assert state["mapping"][0]["source"] == str(source / "clip.mkv")
    cleanup(output, False, False)
    assert (source / "clip.mkv").exists()
    cleanup(output, True, True)
    assert not (source / "clip.mkv").exists()


def test_entire_selection_checked_before_deletion_and_new_sidecars_block(tmp_path):
    source, output = completed_job(tmp_path, 2)
    for kind in ("visual", "editor"):
        record_acceptance(
            output,
            kind,
            "accept",
            "Test user",
            editor="Test NLE 1",
            project_copy="copy",
            note="Reviewed both files",
        )
    (source / "clip.xmp").write_text("required sidecar")
    assert inspect_acceptance(output)["eligible"] == []
    with pytest.raises(ValueError, match="acceptance"):
        cleanup(output, True, True)
    (source / "clip.xmp").unlink()
    manifest = json.loads((output / "archive-manifest.json").read_text())
    Path(manifest["records"][1]["output"]).write_bytes(b"changed second output")
    with pytest.raises(ValueError, match="changed"):
        cleanup(output, True, True)
    assert (source / "clip.mkv").exists()
    assert (source / "second.mkv").exists()


def test_unmet_requirement_and_missing_editor_copy_cannot_be_accepted(tmp_path):
    source, output = completed_job(tmp_path)
    with pytest.raises(ValueError, match="project copy"):
        record_acceptance(output, "editor", "accept", "User", editor="NLE 1", note="Reopened")
    record_acceptance(
        output,
        "visual",
        "reject",
        "User",
        note="Missing camera metadata",
        unmet_requirements=["proprietary camera metadata"],
    )
    with pytest.raises(ValueError, match="keep originals"):
        record_acceptance(
            output,
            "visual",
            "accept",
            "User",
            note="Not preserved",
            unmet_requirements=["proprietary camera metadata"],
        )
    assert inspect_acceptance(output)["eligible"] == []
    assert (source / "clip.mkv").exists()


def test_changed_settings_or_outputs_invalidate_acceptance(tmp_path):
    source, output = completed_job(tmp_path)
    for kind in ("visual", "editor"):
        record_acceptance(
            output,
            kind,
            "accept",
            "Test user",
            editor="Test NLE 1",
            project_copy="copy",
            note="Reviewed",
        )
    manifest_path = output / "archive-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["records"][0]["settings"]["quality"] = 29
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="settings"):
        cleanup(output, True, True)
    assert (source / "clip.mkv").exists()
    manifest["records"][0]["settings"]["quality"] = 30
    manifest_path.write_text(json.dumps(manifest))
    Path(manifest["records"][0]["output"]).write_bytes(b"changed")
    with pytest.raises(ValueError, match="changed"):
        cleanup(output, True, True)
    assert (source / "clip.mkv").exists()
