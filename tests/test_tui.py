import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from textual.widgets import (
    Checkbox,
    Input,
    Select,
    SelectionList,
    Button,
    Collapsible,
    DataTable,
    Static,
)

from archivebench.core import save
from archivebench.presets import make_preset
from archivebench.selection import selected_job
from archivebench.tui import ArchiveApp


def test_tui_ignores_change_events_before_mount(tmp_path):
    app = ArchiveApp(library=tmp_path / "empty-library")
    app.on_input_changed(Input.Changed(Input(id="output"), "archive"))
    app.on_selection_list_selected_changed()
    app.on_checkbox_changed(Checkbox.Changed(Checkbox(id="scope-accept"), True))
    app.on_select_changed(Select.Changed(Select([], id="preset"), str(app.preset_paths[0])))
    assert not app.ui_ready
    assert not app.reviewed


def test_tui_starters_available_without_saved_presets(tmp_path):
    async def exercise():
        app = ArchiveApp(library=tmp_path / "empty-library")
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            assert app.ui_ready
            table = app.query_one("#preset-table", DataTable)
            assert table.row_count == 4
            app.query_one("#preset", Select).value = str(app.preset_paths[0])
            await pilot.pause()
            assert "Quality priority" in str(app.query_one("#summary", Static).content)
            assert "untested on your footage" in str(app.query_one("#summary", Static).content)
            assert app.query_one("#preset-technical", Collapsible).collapsed
            details = str(app.query_one("#preset-details", Static).content)
            assert "CRF 20" in details
            assert "-preset medium" in details
            assert "Match source" in details
            assert "yuv420p is a template placeholder" in details
            assert "Actual pixel format matches each source clip" in details
            assert app.query_one("#audio", Select).value == "copy"
            assert not (tmp_path / "empty-library").exists()

    asyncio.run(exercise())


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
            assert not app.reviewed
            assert app.query_one("#start", Button).disabled
            assert not (output / "archive-manifest.json").exists()
            app.query_one("#scope-accept", Checkbox).value = True
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
            app.query_one("#audio", Select).value = "none"
            await pilot.pause()
            assert not app.query_one("#scope-accept", Checkbox).value

    asyncio.run(exercise())


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_tui_rejected_choice_offers_probed_alternatives_without_selecting_one(tmp_path):
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
            "testsrc2=size=64x64:rate=10",
            "-t",
            "0.5",
            "-c:v",
            "ffv1",
            "-pix_fmt",
            "yuv422p10le",
            str(source / "a.mkv"),
        ],
        check=True,
    )
    library = tmp_path / "presets"
    document = library / "rejected.json"
    save(
        document,
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libsvtav1",
                "quality": 30,
                "pixel_format": "source",
            }
        ),
    )
    output = tmp_path / "output"
    job_path = tmp_path / "job.json"
    job = selected_job(source, output, document, ["a.mkv"], {})
    save(job_path, job)

    async def exercise():
        app = ArchiveApp(library=library, job=job_path)
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            app.prepare()
            await app.workers.wait_for_complete()
            offered = str(app.query_one("#alternatives", Static).content)
            assert "Balanced (AVC alternative): short probes passed" in offered
            assert "Choose a preset above explicitly" in offered
            assert json.loads(job_path.read_text()) == job
            assert not (output / "archive-manifest.json").exists()
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
            app.query_one("#scope-accept", Checkbox).value = True
            app.prepare()
            await app.workers.wait_for_complete()
            assert app.reviewed
            app.run_engine(True)
            log_path = output / "archive-job.json.log"
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


def test_tui_postjob_tradeoff_and_separate_deletion(tmp_path):
    from tests.test_acceptance import completed_job

    source, output = completed_job(tmp_path)
    job_path = tmp_path / "completed.job.json"
    save(job_path, json.loads((output / "archive-manifest.json").read_text())["job"])

    async def exercise():
        app = ArchiveApp(library=tmp_path / "presets", job=job_path)
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            assert app.query_one("#delete-originals", Button).disabled
            app.query_one("#acceptance-name", Input).value = "User"
            app.query_one(
                "#acceptance-note", Input
            ).value = "Accept quality loss without inspection"
            app.postjob("accept-tradeoff")
            await app.workers.wait_for_complete()
            assert (source / "clip.mkv").exists()
            assert app.query_one("#delete-originals", Button).disabled
            app.postjob("preview-deletion")
            await app.workers.wait_for_complete()
            assert str(source / "clip.mkv") in str(
                app.query_one("#deletion-preview", Static).content
            )
            assert not app.query_one("#delete-originals", Button).disabled
            assert (source / "clip.mkv").exists()
            app.postjob("delete-originals")
            await app.workers.wait_for_complete()
            assert not (source / "clip.mkv").exists()

    asyncio.run(exercise())


def test_tui_deletion_preview_expires_on_new_consent_or_destination_change(tmp_path):
    from archivebench.acceptance import record_acceptance
    from tests.test_acceptance import completed_job

    source, output = completed_job(tmp_path)
    job_path = tmp_path / "completed.job.json"
    save(job_path, json.loads((output / "archive-manifest.json").read_text())["job"])
    record_acceptance(output, "quality-tradeoff", "accept", "User", note="Accept loss")

    async def exercise():
        app = ArchiveApp(library=tmp_path / "presets", job=job_path)
        async with app.run_test(size=(120, 60)) as pilot:
            await pilot.pause()
            app.postjob("preview-deletion")
            await app.workers.wait_for_complete()
            record_acceptance(output, "quality-tradeoff", "accept", "User", note="Renew decision")
            app.postjob("delete-originals")
            await app.workers.wait_for_complete()
            assert (source / "clip.mkv").exists()
            assert app.query_one("#delete-originals", Button).disabled
            app.postjob("preview-deletion")
            await app.workers.wait_for_complete()
            app.query_one("#output", Input).value = str(tmp_path / "other-output")
            await pilot.pause()
            assert app.query_one("#delete-originals", Button).disabled
            app.set_busy(True)
            app.postjob("delete-originals")
            await app.workers.wait_for_complete()
            assert (source / "clip.mkv").exists()
            app.set_busy(False)

    asyncio.run(exercise())
