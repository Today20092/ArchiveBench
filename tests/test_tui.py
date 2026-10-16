import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from textual.widgets import Input, Select, SelectionList, Button

from archivebench.core import save
from archivebench.presets import make_preset
from archivebench.selection import selected_job
from archivebench.tui import ArchiveApp


def preset(library):
    path = library / "test.json"
    save(
        path,
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 30,
                "pixel_format": "source",
            }
        ),
    )
    return path


def test_tui_mixed_paths_and_review_errors(tmp_path):
    async def exercise():
        first, second = tmp_path / "SD 1", tmp_path / "SD 2"
        first.mkdir()
        second.mkdir()
        (first / "same.mov").touch()
        (second / "same.mov").touch()
        library = tmp_path / "presets"
        preset(library)
        app = ArchiveApp([first, second, first / "same.mov"], library)
        async with app.run_test(size=(120, 60)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            clips = app.query_one("#clips", SelectionList)
            assert len(clips.selected) == 2
            assert not app.reviewed
            assert app.query_one("#start", Button).disabled
            clips.deselect_all()
            assert clips.selected == []
            app.prepare()
            await app.workers.wait_for_complete()
            assert app.job_path is None
            assert not app.busy
            app.query_one("#preset", Select).value = str(library / "test.json")
            await pilot.pause()
            assert app.query_one("#output", Input).value == str(tmp_path / "Archived Footage")

    asyncio.run(exercise())


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_tui_real_encode_resume(tmp_path):
    source = tmp_path / "source ليلة"
    source.mkdir()
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
            "2",
            "-c:v",
            "ffv1",
            str(source / "a.mkv"),
        ],
        check=True,
    )
    library = tmp_path / "presets"
    document = preset(library)
    job_path = tmp_path / "saved.job.json"
    output = tmp_path / "output"
    save(job_path, selected_job(source, output, document, ["a.mkv"], {}))

    async def exercise():
        app = ArchiveApp(library=library, job=job_path)
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            app.prepare()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.reviewed
            app.run_engine(True)
            await app.workers.wait_for_complete()
            record = json.loads((output / "archive-manifest.json").read_text())["records"][0]
            assert record["status"] == "verified"
            target = Path(record["output"])
            modified = target.stat().st_mtime_ns
            app.prepare()
            await app.workers.wait_for_complete()
            app.run_engine(True)
            await app.workers.wait_for_complete()
            assert target.stat().st_mtime_ns == modified
            assert not (output / ".lock").exists()
            assert (source / "a.mkv").exists()

    asyncio.run(exercise())


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_progress_stop_waits_for_child(monkeypatch):
    from archivebench.progress import encode_progress

    processes = []
    original = subprocess.Popen

    def track(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", track)

    with pytest.raises(KeyboardInterrupt):
        encode_progress(
            [
                "ffmpeg",
                "-re",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=64x64:rate=10",
                "-t",
                "60",
                "-f",
                "null",
                "-",
            ],
            10,
            lambda: True,
        )
    assert processes and all(p.poll() is not None for p in processes)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_tui_interrupt_then_resume_same_job(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30",
            "-t",
            "8",
            "-c:v",
            "ffv1",
            str(source / "a.mkv"),
        ],
        check=True,
    )
    library = tmp_path / "presets"
    document = library / "test.json"
    save(
        document,
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "preset": "veryslow",
                "quality": 30,
                "pixel_format": "source",
            }
        ),
    )
    output = tmp_path / "output"
    job_path = tmp_path / "saved.job.json"
    save(job_path, selected_job(source, output, document, ["a.mkv"], {}))

    async def exercise():
        app = ArchiveApp(library=library, job=job_path)
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            app.prepare()
            await app.workers.wait_for_complete()
            assert app.reviewed
            app.run_engine(True)
            log_path = Path(str(job_path) + ".log")
            for _ in range(600):
                if log_path.exists() and "Encoding:" in log_path.read_text():
                    break
                await asyncio.sleep(0.05)
            else:
                pytest.fail("Encode did not start")
            app.request_stop()
            await app.workers.wait_for_complete()
            assert app.process is None and not app.busy
            assert "Stopped safely" in log_path.read_text()
            assert not (output / ".lock").exists()
            assert (
                json.loads((output / "archive-manifest.json").read_text())["records"][0]["status"]
                == "pending"
            )
            app.prepare()
            await app.workers.wait_for_complete()
            assert app.reviewed
            app.run_engine(True)
            await app.workers.wait_for_complete()
            assert (
                json.loads((output / "archive-manifest.json").read_text())["records"][0]["status"]
                == "verified"
            )
            assert (source / "a.mkv").exists()

    asyncio.run(exercise())
