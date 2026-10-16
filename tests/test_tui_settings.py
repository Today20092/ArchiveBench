import asyncio
import json

from textual.widgets import DataTable, Input, Select, Static, TabbedContent

from archivebench.core import save
from archivebench.presets import make_preset, resolve_settings
from archivebench.tui import ArchiveApp, preset_description
from archivebench.window import centered_bounds


def test_navigation_keeps_current_summaries_without_rewriting(tmp_path, monkeypatch):
    async def exercise():
        app = ArchiveApp(library=tmp_path)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            app.query_one("#output", Input).value = str(tmp_path / "archive")
            summary = app.query_one("#review-summary", Static)
            for _ in range(40):
                if str(tmp_path / "archive") in str(summary.content):
                    break
                await pilot.pause(0.05)
            assert str(tmp_path / "archive") in str(summary.content)
            updates = []
            original = summary.update

            def track(content="", **kwargs):
                updates.append(content)
                return original(content, **kwargs)

            monkeypatch.setattr(summary, "update", track)
            for _ in range(2):
                await pilot.click("#next")
                await pilot.pause(0.4)
            assert app.query_one(TabbedContent).active == "step-review"
            assert not updates
            await pilot.click("#back")
            app.query_one("#output", Input).value = str(tmp_path / "changed")
            for _ in range(40):
                if str(tmp_path / "changed") in str(summary.content):
                    break
                await pilot.pause(0.05)
            assert str(tmp_path / "changed") in str(summary.content)
            assert not app.reviewed
            await pilot.resize_terminal(80, 25)
            await pilot.click("#next")
            assert summary.region.width > 0
            assert app.query_one("#next").region.bottom <= app.size.height

    asyncio.run(exercise())


def test_readable_settings_and_aac_job(tmp_path, monkeypatch):
    async def exercise():
        source = tmp_path / "source"
        source.mkdir()
        (source / "clip.mov").touch()
        library = tmp_path / "presets"
        library.mkdir()
        path = library / "test.json"
        document = make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 30,
                "pixel_format": "source",
            }
        )
        document["scope"] = {"environment": {"ffmpeg": "PRIVATE BUILD FLAGS"}, "footage": []}
        save(path, document)
        app = ArchiveApp([source], library)

        async def no_preflight(execute):
            pass

        monkeypatch.setattr(app, "execute_engine", no_preflight)
        async with app.run_test(size=(100, 35)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.click("#next")
            assert app.query_one(TabbedContent).active == "step-settings"
            app.query_one("#preset-table", DataTable).focus()
            await pilot.press("enter")
            await pilot.pause()
            assert app.query_one("#preset", Select).value == str(path)
            device = app.query_one("#preset-table", DataTable).get_row(str(path))[2]
            assert device.plain == "CPU"
            assert str(device.spans[0].style) == "bold #ddd6fe"
            assert (
                app.query_one("#preset-table", DataTable).cursor_foreground_priority == "renderable"
            )
            assert "PRIVATE BUILD FLAGS" not in str(app.query_one("#summary", Static).render())
            assert not app.query_one("#aac-options").display
            app.query_one("#audio", Select).value = "aac"
            await pilot.pause()
            app.query_one("#aac-bitrate", Select).value = 128
            await pilot.pause()
            assert app.query_one("#aac-options").display, (
                app.busy,
                app.query_one("#audio", Select).value,
                str(app.query_one("#status", Static).render()),
            )
            assert "128 kbps per channel" in str(app.query_one("#review-summary", Static).render())
            app.prepare()
            await app.workers.wait_for_complete()
            assert app.job_path is not None, str(app.query_one("#status", Static).render())
            settings = resolve_settings(json.loads(app.job_path.read_text())["preset"])
            assert settings["audio_mode"] == "aac"
            assert settings["audio_kbps_per_channel"] == 128

    asyncio.run(exercise())


def test_preset_facts_and_monitor_position():
    text = preset_description(
        {"encoder": "hevc_nvenc", "quality": 28, "pixel_format": "yuv420p10le"}
    )
    assert "H.265 / HEVC  |  GPU  |  CQ 28" in text
    assert "4:2:0 | 10-bit" in text
    assert "Resolution: Match source" in text
    assert "CRF 24" in preset_description(
        {"encoder": "libx265", "quality": 24, "pixel_format": "source"}
    )
    assert centered_bounds(-1920, 0, 0, 1080) == (-1728, 108, 1536, 864)
