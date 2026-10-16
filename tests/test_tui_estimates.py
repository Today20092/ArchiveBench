import asyncio
import math

from textual.widgets import DataTable, SelectionList, Static

from archivebench.core import save
from archivebench.presets import make_preset
from archivebench.tui import ArchiveApp
from archivebench.tui_estimates import clip_duration, duration_label, measured_rate


def test_historical_rate_validation():
    for rate in (None, True, -1, 0, math.nan, math.inf, "2"):
        assert (
            measured_rate(
                {
                    "evidence": {
                        "estimates": {
                            "basis": "measured",
                            "encode_seconds_per_second": rate,
                        }
                    }
                }
            )
            is None
        )
    assert (
        measured_rate(
            {
                "evidence": {
                    "estimates": {
                        "basis": "unknown",
                        "encode_seconds_per_second": 2,
                    }
                }
            }
        )
        is None
    )
    assert duration_label(3600) == "1h 00m"
    assert duration_label(90) == "1m 30s"


def test_duration_selection_and_missing_evidence(tmp_path, monkeypatch):
    async def exercise():
        source = tmp_path / "source"
        source.mkdir()
        first, second = source / "a.mov", source / "b.mov"
        first.touch()
        second.touch()
        library = tmp_path / "presets"
        known, unknown = library / "known.json", library / "unknown.json"
        document = make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 30,
                "pixel_format": "source",
            }
        )
        save(unknown, document)
        document["evidence"]["estimates"].update(
            basis="measured",
            encode_seconds_per_second=2,
        )
        save(known, document)
        calls = []

        async def duration(path):
            calls.append(path)
            return 900

        monkeypatch.setattr("archivebench.tui.clip_duration", duration)
        app = ArchiveApp([source], library)
        async with app.run_test(size=(120, 40)) as pilot:
            await app.workers.wait_for_complete()
            await pilot.pause()
            table = app.query_one(DataTable)
            assert table.get_cell(str(known), "estimate") == "~1h 00m"
            assert table.get_cell(str(unknown), "estimate") == "No timing data"
            assert "30m 00s" in str(app.query_one("#duration-summary", Static).content)
            clips = app.query_one(SelectionList)
            clips.deselect(str(second))
            await pilot.pause()
            assert table.get_cell(str(known), "estimate") == "~30m 00s"
            assert len(calls) == 2
            app.durations[str(first)] = None
            app.refresh_estimates()
            assert table.get_cell(str(known), "estimate") == "Duration unavailable"
            assert "1 unavailable" in str(app.query_one("#duration-summary", Static).content)
            clips.deselect_all()
            await pilot.pause()
            assert table.get_cell(str(known), "estimate") == "Select clips"

    asyncio.run(exercise())


def test_cancel_duration_probe_reaps_process(monkeypatch, tmp_path):
    async def exercise():
        started = asyncio.Event()

        class Process:
            returncode = None
            killed = False
            waited = False

            async def communicate(self):
                started.set()
                await asyncio.Event().wait()

            def kill(self):
                self.killed = True

            async def wait(self):
                self.waited = True
                self.returncode = -1

        process = Process()

        async def spawn(*args, **kwargs):
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        task = asyncio.create_task(clip_duration(tmp_path / "clip.mov"))
        await started.wait()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        assert process.killed and process.waited

    asyncio.run(exercise())
