import asyncio
import json
import shutil
import subprocess
import threading

import pytest

from textual.widgets import Button, Checkbox, Input, Select, SelectionList, Static, TabbedContent

from archivebench.tui import ArchiveApp


def test_stopping_capability_review_does_not_enable_start(tmp_path, monkeypatch):
    entered, released = threading.Event(), threading.Event()

    def check(config):
        entered.set()
        assert released.wait(5)
        return {"checks": [], "verified_encoders": ["libx265"]}

    monkeypatch.setattr("archivebench.tui.availability", check)

    async def exercise():
        app = ArchiveApp(library=tmp_path / "empty")
        async with app.run_test(size=(120, 60)) as pilot:
            clip = str(tmp_path / "clip.mov")
            app.query_one("#clips", SelectionList).add_option(("clip.mov", clip, True))
            app.durations[clip] = 10
            app.query_one("#comparison-output", Input).value = str(tmp_path / "comparison")
            await pilot.pause()
            app.review_comparison()
            assert await asyncio.to_thread(entered.wait, 5)
            app.request_stop()
            released.set()
            await app.workers.wait_for_complete()
            assert app.query_one("#comparison-start", Button).disabled
            assert not (tmp_path / "comparison" / "config.json").exists()
            assert "stopped" in str(app.query_one("#comparison-brief", Static).content)

    asyncio.run(exercise())


def test_first_use_comparison_requires_review_and_can_sample_selected_starter(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "archivebench.tui.availability",
        lambda _: {"checks": [], "verified_encoders": ["libx265", "libsvtav1"]},
    )

    async def exercise():
        clip = tmp_path / "clip.mov"
        clip.touch()
        app = ArchiveApp(library=tmp_path / "empty")
        async with app.run_test(size=(120, 60)) as pilot:
            app.root = tmp_path
            app.query_one("#clips", SelectionList).add_option(("clip.mov", str(clip), True))
            app.durations[str(clip)] = 20
            app.query_one("#preset", Select).value = str(app.preset_paths[1])
            app.query_one("#comparison-output", Input).value = str(tmp_path / "comparison")
            app.query_one("#comparison-minutes", Input).value = "2"
            await pilot.pause()
            app.query_one(TabbedContent).active = "step-setup"
            await pilot.pause()
            await pilot.click("#comparison-review")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert not app.query_one("#comparison-start", Button).disabled
            brief = str(app.query_one("#comparison-brief", Static).content)
            assert "2.0" in brief and "libx265" in brief and "libsvtav1" in brief
            assert "fresh validation" in brief
            config = json.loads((tmp_path / "comparison" / "config.json").read_text())
            assert config["strategy"] == "fixed"
            assert config["samples"][0]["seconds"] == 5
            app.query_one("#comparison-minutes", Input).value = "3"
            await pilot.pause()
            assert app.query_one("#comparison-start", Button).disabled
            app.query_one("#comparison-kind", Select).value = "sample"
            await pilot.pause()
            await pilot.click("#comparison-review")
            await app.workers.wait_for_complete()
            await pilot.pause()
            config = json.loads((tmp_path / "comparison" / "config.json").read_text())
            assert config["fixed_settings"] == {"libx265": [24]}
            assert "approximate" in str(app.query_one("#comparison-brief", Static).content)
            assert not app.query_one("#scope-accept", Checkbox).value

    asyncio.run(exercise())


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_starter_can_decline_sampling_but_must_accept_uncertain_scope(tmp_path):
    async def exercise():
        clip = tmp_path / "clip.mkv"
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
                "-color_range",
                "tv",
                str(clip),
            ],
            check=True,
        )
        app = ArchiveApp(library=tmp_path / "empty")
        async with app.run_test(size=(120, 60)) as pilot:
            app.root = tmp_path
            app.query_one("#clips", SelectionList).add_option(("clip.mkv", str(clip), True))
            app.query_one("#preset", Select).value = str(app.preset_paths[3])
            app.query_one("#container", Select).value = "mkv"
            app.query_one("#timecode", Select).value = "reject"
            app.query_one("#output", Input).value = str(tmp_path / "output")
            await pilot.pause()
            app.prepare()
            await app.workers.wait_for_complete()
            assert app.job_path is not None
            assert not app.reviewed
            assert app.query_one("#start", Button).disabled
            assert not (tmp_path / "output" / "archive-manifest.json").exists()
            assert not (tmp_path / "output" / "suitability-acceptance.json").exists()
            assert "Accept uncertain" in str(app.query_one("#status", Static).content)
            assert "unknown" in str(app.query_one("#scope-summary", Static).content)
            assert app.comparison_config is None
            app.query_one("#scope-accept", Checkbox).value = True
            app.prepare()
            await app.workers.wait_for_complete()
            assert app.reviewed
            consent = json.loads((tmp_path / "output" / "suitability-acceptance.json").read_text())
            assert consent["status"] == "accepted-uncertain"
            assert not (tmp_path / "output" / "archive-manifest.json").exists()
            assert app.comparison_config is None
            assert clip.exists()

    asyncio.run(exercise())


def test_exported_measured_preset_loads_into_standalone_settings(tmp_path):
    from archivebench.core import save
    from archivebench.presets import make_preset

    document = make_preset(
        {
            "version": 2,
            "type": "archive-settings",
            "encoder": "libx264",
            "quality": 25,
            "pixel_format": "source",
            "evidence_status": "measured-starting-point",
        },
        "Measured example",
    )
    document["scope"]["footage"] = [{"width": 1920, "height": 1080}]
    path = tmp_path / "export.json"
    save(path, document)

    async def exercise():
        app = ArchiveApp(library=tmp_path / "empty")
        async with app.run_test(size=(120, 60)) as pilot:
            app.query_one(TabbedContent).active = "step-setup"
            app.query_one("#import-preset", Input).value = str(path)
            await pilot.pause()
            app.query_one("#import-preset-button", Button).scroll_visible()
            await pilot.pause()
            await pilot.click("#import-preset-button")
            await pilot.pause()
            assert app.query_one("#preset", Select).value == str(path)
            assert app.query_one(TabbedContent).active == "step-settings"
            scope = str(app.query_one("#scope-summary", Static).content)
            assert "1920" in scope and "measured-starting-point" in scope and "unvalidated" in scope
            assert not app.query_one("#scope-accept", Checkbox).value

    asyncio.run(exercise())


def test_standalone_sample_runs_shared_engine_and_keeps_original(tmp_path):
    import shutil
    import subprocess
    import pytest

    if (
        not shutil.which("ffmpeg")
        or "libvmaf"
        not in subprocess.run(
            ["ffmpeg", "-filters"], capture_output=True, text=True, check=True
        ).stdout
    ):
        pytest.skip("FFmpeg with libvmaf required")
    clip = tmp_path / "clip.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=192x108:rate=10",
            "-t",
            "2",
            "-c:v",
            "ffv1",
            str(clip),
        ],
        check=True,
    )

    async def exercise():
        app = ArchiveApp(library=tmp_path / "empty")
        async with app.run_test(size=(120, 60)) as pilot:
            app.root = tmp_path
            app.query_one("#clips", SelectionList).add_option(("clip.mkv", str(clip), True))
            app.durations[str(clip)] = 2
            app.query_one("#preset", Select).value = str(app.preset_paths[3])
            app.query_one("#comparison-kind", Select).value = "sample"
            app.query_one("#comparison-output", Input).value = str(tmp_path / "sample")
            app.query_one("#comparison-length", Input).value = "1"
            app.query_one("#comparison-minutes", Input).value = "1"
            await pilot.pause()
            app.review_comparison()
            await app.workers.wait_for_complete()
            assert not app.query_one("#comparison-start", Button).disabled
            app.run_comparison()
            await app.workers.wait_for_complete()
            result = json.loads((tmp_path / "sample" / "results.json").read_text())
            assert result["trials"], result.get("progress")
            assert (tmp_path / "sample" / "report.html").exists()
            assert not app.query_one("#comparison-report", Button).disabled
            assert clip.exists()
            assert not app.reviewed

    asyncio.run(exercise())
