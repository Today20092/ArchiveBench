import copy
import json
import shutil
import subprocess

import pytest

from archivebench.acceptance import record_acceptance
from archivebench.archive import cleanup
from archivebench.cli import main
from archivebench.core import save
from archivebench.jobs import create_job, run_job


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize("explicit_selection", [True, False])
def test_resume_remaining_selection_after_approved_partial_cleanup(
    tmp_path, monkeypatch, explicit_selection
):
    source = tmp_path / "source"
    source.mkdir()
    first, second = source / "first.mkv", source / "second.mkv"
    subprocess.run(
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
            str(first),
        ],
        check=True,
    )
    shutil.copyfile(first, second)
    preset = tmp_path / "preset.json"
    save(
        preset,
        {
            "version": 2,
            "type": "archive-settings",
            "encoder": "libx264",
            "quality": 30,
            "pixel_format": "source",
        },
    )
    output = tmp_path / "output"
    job = create_job(source, output, preset)
    if explicit_selection:
        job["selected_files"] = ["first.mkv", "second.mkv"]
    config = tmp_path / "job.json"
    save(config, job)
    archived = output / "first.mkv.archive.mkv"
    with pytest.raises(KeyboardInterrupt):
        run_job(config, True, stop_requested=archived.exists, accept_uncertain_suitability=True)
    consent = json.loads((output / "suitability-acceptance.json").read_text())
    assert len(consent["scope"]) == 2, (
        "Both synthetic sources must pass the initial compatibility probes"
    )
    record_acceptance(
        output, "quality-tradeoff", "accept", "Synthetic user", note="Accept first output"
    )
    cleanup(output, False, False)
    cleanup(output, True, True, selected_sources=[str(first)])
    assert not first.exists() and second.exists()
    manifest_path = output / "archive-manifest.json"
    saved = json.loads(manifest_path.read_text())
    completed = copy.deepcopy(saved["records"][0])
    stamp = archived.stat().st_mtime_ns
    assert run_job(config)["completed_deletions"][0]["status"] == "original_deleted"
    assert run_job(config)["suitability"]["status"] == "accepted-uncertain"
    assert archived.stat().st_mtime_ns == stamp
    resumed_config = tmp_path / "resumed-job.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "archivebench",
            "job",
            "create",
            str(resumed_config),
            "--source",
            str(source),
            "--output",
            str(output),
            "--preset",
            str(preset),
        ],
    )
    main()
    assert json.loads(resumed_config.read_text()) == job
    for field, value in (("settings", {}), ("output", str(output / "wrong.mkv"))):
        tampered = copy.deepcopy(saved)
        tampered["records"][0][field] = value
        save(manifest_path, tampered)
        with pytest.raises(ValueError, match="mapping/settings"):
            run_job(config, True)
        save(manifest_path, saved)
    original_output = archived.read_bytes()
    archived.write_bytes(b"changed")
    with pytest.raises(ValueError, match="replacement changed/missing"):
        run_job(config, True)
    archived.unlink()
    with pytest.raises(ValueError, match="replacement changed/missing"):
        run_job(config, True)
    archived.write_bytes(original_output)
    moved = tmp_path / "unfinished-original.bin"
    second.rename(moved)
    with pytest.raises(ValueError, match="Selected file missing"):
        run_job(config, True)
    moved.rename(second)
    restored_stamp = archived.stat().st_mtime_ns
    run_job(config, True)
    resumed = json.loads(manifest_path.read_text())
    assert resumed["job"] == job
    assert resumed["records"][0] == completed
    assert resumed["records"][1]["status"] == "verified"
    assert not first.exists() and second.exists()
    assert archived.read_bytes() == original_output
    assert archived.stat().st_mtime_ns == restored_stamp
    assert "Original deleted: 1" in (output / "archive-summary.html").read_text()
    assert "Unfinished: 0" in (output / "archive-summary.html").read_text()
