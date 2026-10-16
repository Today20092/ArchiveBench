"""Storage failures stop the shared job lifecycle without touching originals."""

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from archivebench.core import run, save
from archivebench.jobs import create_job, discover_job, run_job
from archivebench.progress import encode_progress


def test_progress_monitor_stops_a_silent_child(monkeypatch):
    processes = []
    popen = subprocess.Popen

    def track(*args, **kwargs):
        if args[0][0] != sys.executable:
            return popen(*args, **kwargs)
        process = popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", track)
    started = time.monotonic()

    def unavailable():
        if time.monotonic() - started > 0.2:
            raise OSError("Destination disconnected")

    with pytest.raises(OSError, match="disconnected"):
        encode_progress(
            [sys.executable, "-c", "import time; time.sleep(30)"], 30, check_storage=unavailable
        )
    assert time.monotonic() - started < 10
    assert processes and all(process.poll() is not None for process in processes)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
@pytest.mark.parametrize("failure", ["low-space", "disconnect"])
def test_storage_stop_retains_original_and_resumes(tmp_path, monkeypatch, failure):
    source, output = tmp_path / "source", tmp_path / "output"
    source.mkdir()
    clip = source / "clip.mkv"
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
            str(clip),
        ]
    )
    original = clip.read_bytes()
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
    job = create_job(source, output, preset)
    config = tmp_path / "original-job.json"
    save(config, job)
    disk_usage = shutil.disk_usage
    checks = 0

    def unavailable(path):
        nonlocal checks
        checks += 1
        usage = disk_usage(path)
        if checks > 2:
            if failure == "disconnect":
                raise OSError("Destination disconnected")
            return usage._replace(free=0)
        return usage

    with monkeypatch.context() as broken:
        broken.setattr(shutil, "disk_usage", unavailable)
        with pytest.raises(OSError, match="Low disk|disconnected"):
            run_job(config, True)
    manifest = json.loads((output / "archive-manifest.json").read_text())
    assert manifest["last_run"].startswith("stopped:")
    assert clip.read_bytes() == original
    assert not (output / ".lock").exists()
    assert discover_job(output) == job
    local_job = output / "archive-job.json"
    assert json.loads(local_job.read_text()) == job
    assert manifest["job_path"] == str(local_job.resolve())
    config.unlink()
    run_job(local_job, True)
    records = json.loads((output / "archive-manifest.json").read_text())["records"]
    assert records[0]["status"] == "verified"
    archived = Path(records[0]["output"])
    stamp = archived.stat().st_mtime_ns
    run_job(local_job, True)
    assert archived.stat().st_mtime_ns == stamp
    assert clip.read_bytes() == original


def test_progress_deadline_stops_a_silent_child(monkeypatch):
    popen = subprocess.Popen
    children = []

    def silent(args, **kwargs):
        if args[0] == "silent-encoder":
            process = popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
            children.append(process)
            return process
        return popen(args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", silent)
    with pytest.raises(TimeoutError, match="time limit"):
        encode_progress(["silent-encoder"], 30, timeout=0.2)
    assert children and all(process.poll() is not None for process in children)
