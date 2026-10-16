import json
import shutil
import subprocess

import pytest

from archivebench.core import save
from archivebench.jobs import create_job, run_job


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_saved_job_requires_bound_suitability_acceptance_before_encoding(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    clip = source / "clip.mkv"
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
            "0.5",
            "-c:v",
            "ffv1",
            str(clip),
        ],
        check=True,
    )
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
    config = tmp_path / "job.json"
    job = create_job(source, output, preset)
    save(config, job)
    assert run_job(config)["suitability"]["status"] == "acceptance-required"
    with pytest.raises(ValueError, match="uncertain.*suitability"):
        run_job(config, True)
    assert not (output / "archive-manifest.json").exists()
    accepted = run_job(config, accept_uncertain_suitability=True)
    assert accepted["suitability"]["status"] == "accepted-uncertain"
    assert json.loads(config.read_text()) == job
    run_job(config, True)
    assert run_job(config)["suitability"]["status"] == "accepted-uncertain"
    assert "accepted-uncertain" in (output / "archive-summary.html").read_text()
    changed = {**job, "selected_files": ["clip.mkv"]}
    save(config, changed)
    assert run_job(config)["suitability"]["status"] == "acceptance-required"
    save(config, job)
    assert run_job(config)["suitability"]["status"] == "accepted-uncertain"
    # Changing the source identity invalidates consent even with identical characteristics.
    clip.touch()
    assert run_job(config)["suitability"]["status"] == "acceptance-required"
    assert clip.exists()
