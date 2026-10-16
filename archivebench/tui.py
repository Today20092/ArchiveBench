"""Interactive archival front end over immutable archive jobs."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

from rich.text import Text

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    SelectionList,
    Static,
    TabbedContent,
    TabPane,
)

from .core import save
from .encoders import SPECS
from .jobs import validate_job
from .presets import resolve_settings
from .selection import selected_job, selection_defaults
from .tui_estimates import clip_duration, duration_label, measured_rate


def preset_facts(settings):
    encoder = settings["encoder"]
    spec = SPECS.get(encoder)
    codec = (
        {"hevc": "H.265 / HEVC", "h264": "H.264 / AVC", "av1": "AV1", "vp9": "VP9"}.get(
            spec[0], spec[0]
        )
        if spec
        else encoder
    )
    control = spec[4][-1].lstrip("-").upper() if spec else "QUALITY"
    hardware = "CPU" if encoder.startswith("lib") else "GPU"
    pixel = settings["pixel_format"]
    color = {
        "source": "Match source chroma and bit depth",
        "yuv420p10le": "4:2:0 | 10-bit",
        "yuv422p10le": "4:2:2 | 10-bit",
        "yuv420p": "4:2:0 | 8-bit",
    }.get(pixel, pixel)
    resolution = (
        "Match source"
        if settings.get("resolution") in (None, "", "original", "source")
        else settings["resolution"]
    )
    return codec, hardware, f"{control} {settings['quality']}", color, resolution


def preset_description(settings):
    codec, hardware, quality, color, resolution = preset_facts(settings)
    return f"{codec}  |  {hardware}  |  {quality}\nColor: {color}\nResolution: {resolution}\n" + (
        "Preserves source color format; video is re-encoded."
        if settings["pixel_format"] == "source"
        else "Color conversion: may reduce source chroma / bit depth."
    )


class StopDialog(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label(
                "Stop this job? Completed outputs stay saved. Interrupted clips restart on resume."
            )
            yield Button("Keep running", id="keep")
            yield Button("Stop safely", id="confirm-stop", variant="warning")

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(event.button.id == "confirm-stop")


class ArchiveApp(App):
    TITLE = "ArchiveBench — archive footage"
    CSS = """
    Screen { layout: vertical; }
    VerticalScroll { height: 1fr; padding: 0 1; }
    Horizontal { height: auto; }
    Button { margin: 0 1 0 0; }
    TabbedContent { height: 1fr; }
    TabPane { padding: 1; }
    SelectionList { height: 1fr; min-height: 8; }
    RichLog { height: 1fr; min-height: 8; }
    #status, #summary, #selection-summary, #review-summary { height: auto; padding: 1; }
    Input, Select, SelectionList, Button { border: none; }
    Label { margin-top: 1; }
    #navigation { padding: 0 1; }
    #aac-options { height: auto; }
    #preset { display: none; }
    #preset-table { height: auto; max-height: 12; margin-bottom: 1; background: #0f172a; }
    DataTable > .datatable--header { background: #334155; color: #f1f5f9; text-style: bold; }
    DataTable > .datatable--cursor { background: #075985; color: #ffffff; }
    Button { background: #334155; color: #f1f5f9; }
    Button:focus { background: #0369a1; color: #ffffff; text-style: bold; }
    Screen { background: #0f172a; color: #e2e8f0; }
    Header, Footer, #navigation { background: #1e293b; color: #e2e8f0; }
    #status { background: #1e293b; color: #cbd5e1; }
    Input, SelectCurrent, SelectionList, RichLog { background: #1e293b; color: #e2e8f0; }
    SelectCurrent { border: none; }
    .section-title { color: #7dd3fc; text-style: bold; margin-top: 1; }
    .hint { color: #cbd5e1; height: auto; margin-bottom: 1; }
    #summary { background: #1e293b; color: #bae6fd; }
    #output { background: #1e293b; color: #f8fafc; }
    #output:focus { background: #334155; }
    Collapsible { border: none; background: #1e293b; padding: 1; margin-top: 1; }
    StopDialog { align: center middle; }
    StopDialog VerticalScroll { width: 70; height: 12; background: $surface; border: thick $warning; }
    """
    BINDINGS = [("ctrl+q", "safe_quit", "Quit safely"), ("ctrl+c", "safe_quit", "Quit safely")]

    def __init__(self, sources=(), library: Path | None = None, job: Path | None = None):
        super().__init__()
        self.register_theme(
            Theme(
                name="archivebench",
                primary="#0284c7",
                secondary="#64748b",
                accent="#38bdf8",
                foreground="#e2e8f0",
                background="#0f172a",
                surface="#1e293b",
                panel="#334155",
                success="#34d399",
                warning="#fbbf24",
                error="#fb7185",
                dark=True,
            )
        )
        self.theme = "archivebench"
        self.sources = list(sources)
        self.library = library or Path.home() / "Documents" / "ArchiveBench Presets"
        self.initial_job = job
        self.root: Path | None = None
        self.job_path: Path | None = None
        self.job_hash = ""
        self.reviewed = False
        self.busy = False
        self.process: asyncio.subprocess.Process | None = None
        self.stop_pending = False
        self.quit_pending = False
        self.default_output = ""
        self.preset_paths = sorted(self.library.glob("*.json"))
        self.preset_rates: dict[str, float | None] = {}
        self.durations: dict[str, float | None] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("1 Clips", id="step-clips"):
                yield Label(
                    "1. Sources — add a folder or clip path; Space toggles clips. One source drive per job."
                )
                yield Input(placeholder="Paste a folder or file path", id="source")
                with Horizontal():
                    yield Button("Add folder / file", id="add")
                    yield Button("Select all", id="all")
                    yield Button("Select none", id="none")
                yield SelectionList[str](id="clips")
                yield Static("No clips selected", id="selection-summary", markup=False)
            with TabPane("2 Settings", id="step-settings"), VerticalScroll():
                yield Label("CHOOSE AN ARCHIVE PRESET", classes="section-title")
                yield Static("No clips selected", id="duration-summary", markup=False)
                yield Static(
                    "Est. encode uses historical benchmark speed. Hardware and footage affect it; "
                    "audio processing and verification take additional time. Estimates use the "
                    "current clip selection, not a saved resume job.",
                    classes="hint",
                )
                yield Static(
                    "Click a row or use arrows and Enter. Quality numbers use each encoder's own scale. Scroll horizontally on narrow windows.",
                    classes="hint",
                )
                presets = self.preset_paths
                yield DataTable(id="preset-table", cursor_type="row", zebra_stripes=True)
                if not presets:
                    yield Static(
                        f"No saved presets found in {self.library}", classes="hint", markup=False
                    )
                yield Select(
                    [(p.stem, str(p)) for p in presets], id="preset", prompt="Choose a saved preset"
                )
                yield Static(
                    "Choose a preset to see codec, quality and chroma policy.",
                    id="summary",
                    markup=False,
                )
                yield Label("SAVE ARCHIVED COPIES TO", classes="section-title")
                yield Static(
                    "Edit the output folder below. Selected folders retain their structure inside it. Your original files stay where they are.",
                    classes="hint",
                )
                yield Input(placeholder="Archive destination", id="output")
                yield Label("AUDIO", classes="section-title")
                with Horizontal():
                    yield Select(
                        [("Copy all audio", "copy"), ("AAC audio", "aac"), ("Drop audio", "none")],
                        value="copy",
                        allow_blank=False,
                        id="audio",
                    )
                with VerticalScroll(id="aac-options"):
                    yield Label("AAC bitrate per channel (kbps)")
                    yield Select(
                        [
                            (f"{n} kbps / channel ({n * 2} kbps stereo)", n)
                            for n in (64, 96, 128, 160, 192, 256, 320, 512)
                        ],
                        value=192,
                        allow_blank=False,
                        id="aac-bitrate",
                    )
                with Collapsible(title="Advanced: container, timecode and data", collapsed=True):
                    yield Label("File container", classes="section-title")
                    yield Static(
                        "MOV, MP4 or MKV wraps the encoded video and audio. Preflight checks compatibility.",
                        classes="hint",
                    )
                    yield Select(
                        [
                            ("Container: MOV", "mov"),
                            ("Container: MP4", "mp4"),
                            ("Container: MKV", "mkv"),
                        ],
                        value="mov",
                        allow_blank=False,
                        id="container",
                    )
                    yield Label("Camera timecode", classes="section-title")
                    yield Static(
                        "Preserve keeps timecode for editing. Reject stops if timecode is present. Drop removes it.",
                        classes="hint",
                    )
                    yield Select(
                        [
                            ("Preserve timecode", "preserve"),
                            ("Reject timecode", "reject"),
                            ("Drop timecode", "drop"),
                        ],
                        value="preserve",
                        allow_blank=False,
                        id="timecode",
                    )
                    yield Label("Other data tracks", classes="section-title")
                    yield Static(
                        "Reject stops when unsupported data tracks are found. Drop explicitly discards those tracks.",
                        classes="hint",
                    )
                    yield Select(
                        [("Reject other data", "reject"), ("Drop other data", "drop")],
                        value="reject",
                        allow_blank=False,
                        id="data",
                    )
            with TabPane("3 Review", id="step-review"), VerticalScroll():
                yield Static("Choose clips and a preset first.", id="review-summary", markup=False)
                yield Label(
                    "3. Review new job, or resume an existing saved job (saved job takes priority)"
                )
                yield Input(
                    value=str(self.initial_job or ""),
                    placeholder="Optional existing .job.json path",
                    id="saved-job",
                )
                with Horizontal():
                    yield Button("Review / preflight", id="review", variant="primary")
                    yield Button(
                        "Start / resume reviewed job", id="start", disabled=True, variant="success"
                    )
            with TabPane("4 Progress", id="step-progress"):
                yield Button("Stop safely", id="stop", disabled=True, variant="warning")
                yield RichLog(id="log", wrap=True, markup=False, highlight=False, max_lines=2000)
        with Horizontal(id="navigation"):
            yield Button("Back", id="back")
            yield Button("Next", id="next", variant="primary")
        yield Static(
            "Ready. No encoding starts until you review and select Start.",
            id="status",
            markup=False,
        )
        yield Footer()

    def on_mount(self):
        table = self.query_one("#preset-table", DataTable)
        table.add_columns("Preset", "Codec", "Device", "Quality")
        table.add_column("Est. encode", key="estimate")
        table.add_columns("Color / bit depth", "Resolution")
        for path in self.preset_paths:
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                facts = preset_facts(resolve_settings(document))
                self.preset_rates[str(path)] = measured_rate(document)
            except (OSError, ValueError, KeyError):
                facts = ("Invalid preset", "-", "-", "-", "-")
            cells = [Text(str(value)) for value in facts]
            cells[1].stylize({"CPU": "bold #ddd6fe", "GPU": "bold #fde68a"}.get(facts[1], ""))
            table.add_row(Text(path.stem), *cells[:3], "Select clips", *cells[3:], key=str(path))
        table.cursor_foreground_priority = "renderable"
        self.query_one("#aac-options").display = False
        if self.sources:
            self.scan(self.sources)

    def invalidate(self):
        self.reviewed = False
        self.query_one("#start", Button).disabled = True
        self.refresh_summary()

    def refresh_summary(self):
        clips = self.query_one("#clips", SelectionList)
        count = f"{len(clips.selected)} of {clips.option_count} clips selected"
        self.query_one("#selection-summary", Static).update(
            f"{count}\nSource folder: {self.root or 'Add a folder or file'}"
        )
        preset = self.query_one("#preset", Select).value
        audio = self.query_one("#audio", Select).value
        audio_text = {"copy": "Copy all tracks unchanged", "none": "Remove all audio"}.get(
            str(audio), f"AAC: {self.query_one('#aac-bitrate', Select).value} kbps per channel"
        )
        saved = self.query_one("#saved-job", Input).value
        self.query_one("#review-summary", Static).update(
            f"Resume saved job: {saved}\nThe saved job's sources and settings take priority."
            if saved
            else f"{count}\n\nFrom: {self.root or 'Not selected'}\n"
            f"To:   {self.query_one('#output', Input).value or 'Not selected'}\n\n"
            f"Preset: {Path(preset).stem if isinstance(preset, str) else 'Not selected'}\n"
            f"Audio: {audio_text}\nContainer: {self.query_one('#container', Select).value}\n"
            f"Timecode: {self.query_one('#timecode', Select).value} | Other data: {self.query_one('#data', Select).value}\n\n"
            "Folder structure is retained. Originals stay intact.\nRun preflight before starting."
        )

    def on_input_changed(self, event: Input.Changed):
        if not self.busy:
            self.invalidate()

    def on_selection_list_selected_changed(self):
        self.refresh_estimates()
        if not self.busy:
            self.invalidate()

    def refresh_estimates(self):
        selected = self.query_one("#clips", SelectionList).selected
        pending = sum(path not in self.durations for path in selected)
        missing = sum(path in self.durations and self.durations[path] is None for path in selected)
        total = sum(self.durations.get(path) or 0 for path in selected)
        state = (
            "Select clips"
            if not selected
            else "Reading durations"
            if pending
            else "Duration unavailable"
            if missing
            else duration_label(total)
        )
        detail = f"{len(selected)} clips selected · Total duration: {state}"
        if pending or missing:
            detail += f" ({pending} pending, {missing} unavailable)"
        summary = self.query_one("#duration-summary", Static)
        if summary.content != detail:
            summary.update(detail)
        table = self.query_one("#preset-table", DataTable)
        for path in self.preset_paths:
            rate = self.preset_rates.get(str(path))
            estimate = (
                "No timing data"
                if rate is None
                else state
                if not selected or pending or missing
                else f"~{duration_label(total * rate)}"
            )
            if table.get_cell(str(path), "estimate") != estimate:
                table.update_cell(str(path), "estimate", estimate, update_width=True)

    @work(exclusive=True, group="durations")
    async def measure_durations(self, paths):
        for path in paths:
            try:
                duration = await clip_duration(path)
            except (OSError, ValueError, asyncio.TimeoutError):
                duration = None
            self.durations[str(path)] = duration
            self.refresh_estimates()

    def on_select_changed(self, event: Select.Changed):
        if self.busy:
            return
        self.invalidate()
        self.query_one("#aac-options").display = self.query_one("#audio", Select).value == "aac"
        if event.select.id == "preset" and isinstance(event.value, str):
            try:
                document = json.loads(Path(event.value).read_text(encoding="utf-8"))
                settings = resolve_settings(document)
                self.query_one("#summary", Static).update(
                    f"SELECTED: {Path(event.value).stem}\n{preset_description(settings)}"
                )
            except (OSError, ValueError) as error:
                self.error(error)

    def error(self, error):
        self.query_one("#status", Static).update(f"Error: {error}")
        self.query_one("#log", RichLog).write(str(error))

    def set_busy(self, value: bool):
        self.busy = value
        for widget in self.query("Input, Select, SelectionList"):
            widget.disabled = value
        for name in ("add", "all", "none", "review"):
            self.query_one(f"#{name}", Button).disabled = value
        self.query_one("#preset-table", DataTable).disabled = value
        self.query_one("#stop", Button).disabled = not value
        self.query_one("#start", Button).disabled = value or not self.reviewed

    @work(exclusive=True, group="scan")
    async def scan(self, sources):
        self.set_busy(True)
        self.stop_pending = False
        self.invalidate()
        clips = self.query_one("#clips", SelectionList)
        previous = set(clips.selected)
        previous_paths = {
            option.value
            for option in (clips.get_option_at_index(i) for i in range(clips.option_count))
        }
        try:
            root, output, rows = await asyncio.to_thread(selection_defaults, sources)
            self.root, self.sources = root, list(sources)
            clips.clear_options()
            clips.add_options(
                [
                    (
                        p.relative_to(root).as_posix(),
                        str(p),
                        str(p) in previous if str(p) in previous_paths else checked,
                    )
                    for p, checked in rows
                ]
            )
            if self.query_one("#output", Input).value in ("", self.default_output):
                self.query_one("#output", Input).value = str(output)
            self.default_output = str(output)
            self.durations.clear()
            self.refresh_estimates()
            self.measure_durations([p for p, _ in rows])
            self.query_one("#status", Static).update(
                "Clips loaded. Select the clips to archive, then continue to Settings."
            )
            self.refresh_summary()
        except (ValueError, OSError) as error:
            self.error(error)
        finally:
            self.set_busy(False)
            if self.quit_pending:
                self.exit()

    async def on_button_pressed(self, event: Button.Pressed):
        action = event.button.id
        if action in ("back", "next"):
            tabs = self.query_one(TabbedContent)
            steps = ("step-clips", "step-settings", "step-review", "step-progress")
            tabs.active = steps[
                max(0, min(3, steps.index(tabs.active) + (1 if action == "next" else -1)))
            ]
        elif action == "add":
            value = self.query_one("#source", Input).value.strip().strip('"')
            if value:
                self.scan([*self.sources, Path(value)])
        elif action in ("all", "none"):
            clips = self.query_one("#clips", SelectionList)
            clips.select_all() if action == "all" else clips.deselect_all()
        elif action == "review":
            self.prepare()
        elif action == "start" and self.reviewed:
            self.run_engine(True)
        elif action == "stop":
            self.push_screen(StopDialog(), self.confirm_stop)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if not self.busy and event.row_key.value is not None:
            self.query_one("#preset", Select).value = event.row_key.value

    @work(exclusive=True, group="prepare")
    async def prepare(self):
        self.set_busy(True)
        self.stop_pending = False
        self.invalidate()
        try:
            saved = self.query_one("#saved-job", Input).value.strip().strip('"')
            if saved:
                path = Path(saved)
                job = json.loads(path.read_text(encoding="utf-8"))
                validate_job(job)
            else:
                preset = self.query_one("#preset", Select).value
                output = self.query_one("#output", Input).value.strip().strip('"')
                if self.root is None or not isinstance(preset, str) or not output:
                    raise ValueError("Add sources, choose a preset and enter a destination")
                selected = [
                    Path(p).relative_to(self.root).as_posix()
                    for p in self.query_one("#clips", SelectionList).selected
                ]
                policies = {
                    "container": self.query_one("#container", Select).value,
                    "audio_mode": self.query_one("#audio", Select).value,
                    "timecode_mode": self.query_one("#timecode", Select).value,
                    "data_mode": self.query_one("#data", Select).value,
                    "audio_kbps_per_channel": self.query_one("#aac-bitrate", Select).value,
                }
                job = await asyncio.to_thread(
                    selected_job, self.root, Path(output), Path(preset), selected, policies
                )
                path = Path(str(job["output_root"]) + ".job.json")
                if path.exists():
                    if json.loads(path.read_text(encoding="utf-8")) != job:
                        raise ValueError(
                            "Destination has a different saved job. Load it to resume or choose another destination."
                        )
                else:
                    save(path, job)
            self.job_path = path.resolve()
            self.job_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            self.query_one("#log", RichLog).write(
                f"Saved job: {self.job_path}\nSource: {job['source_root']}\nOutput: {job['output_root']}\nSettings: {resolve_settings(job['preset'])}\nSelected: {job.get('selected_files', 'All eligible files')}"
            )
        except (ValueError, OSError) as error:
            self.error(error)
            self.set_busy(False)
            return
        self.set_busy(False)
        if self.stop_pending:
            self.query_one("#status", Static).update(
                "Stopped before preflight; no encoding started."
            )
            if self.quit_pending:
                self.exit()
            return
        await self.execute_engine(False)

    @work(exclusive=True, group="engine")
    async def run_engine(self, execute: bool):
        await self.execute_engine(execute)

    async def execute_engine(self, execute: bool):
        if self.busy or self.job_path is None:
            return
        self.set_busy(True)
        self.query_one(TabbedContent).active = "step-progress"
        self.stop_pending = False
        log_path = Path(str(self.job_path) + ".log")
        try:
            if hashlib.sha256(self.job_path.read_bytes()).hexdigest() != self.job_hash:
                raise ValueError("Saved job changed; review it again")
            self.query_one("#status", Static).update(
                f"{'Encoding / verifying' if execute else 'Preflight'} — log: {log_path}"
            )
            self.process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                "-m",
                "archivebench.tui_worker",
                str(self.job_path),
                *(["--execute"] if execute else []),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            assert self.process.stdout is not None
            if self.stop_pending:
                self.request_stop()
            with log_path.open("a", encoding="utf-8") as log:
                async for line in self.process.stdout:
                    text = line.decode("utf-8", errors="replace").rstrip()
                    log.write(text + "\n")
                    log.flush()
                    self.query_one("#log", RichLog).write(text)
            code = await self.process.wait()
            self.reviewed = code == 0 and not execute
            status = (
                "Preflight finished. Check the Progress log, then return to Review to start."
                if self.reviewed
                else "Processing finished. Check failed / kept-original records; visual acceptance is still required."
                if code == 0
                else "Stopped. Review the saved job to resume; completed files are retained."
                if code == 130
                else "Job failed. See the log; originals are retained."
            )
            self.query_one("#status", Static).update(status)
        except (OSError, ValueError) as error:
            self.reviewed = False
            self.error(error)
        finally:
            if self.process and self.process.stdin:
                self.process.stdin.close()
            if self.process and self.process.returncode is None:
                await self.process.wait()
            self.process = None
            self.set_busy(False)
            if self.quit_pending:
                self.exit()

    def request_stop(self):
        self.stop_pending = True
        self.query_one("#status", Static).update(
            "Stopping — waiting for owned FFmpeg cleanup or the current preflight/verification step. Do not close the terminal."
        )
        if self.process and self.process.stdin and not self.process.stdin.is_closing():
            self.process.stdin.write(b"stop\n")

    def confirm_stop(self, confirmed: bool | None):
        if confirmed:
            self.request_stop()
        else:
            self.quit_pending = False

    def action_safe_quit(self):
        if self.busy:
            self.quit_pending = True
            self.push_screen(StopDialog(), self.confirm_stop)
        else:
            self.exit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", type=Path)
    parser.add_argument("--preset-directory", type=Path)
    parser.add_argument("--job", type=Path, help="Review/resume an immutable saved job")
    parser.add_argument(
        "--fit-window",
        action="store_true",
        help="Center a dedicated Windows console at 80%% of the monitor work area",
    )
    args = parser.parse_args()
    if args.fit_window and sys.platform == "win32":
        from .window import fit_console_window

        fit_console_window()
    try:
        ArchiveApp(args.sources, args.preset_directory, args.job).run()
    except Exception as error:
        print(f"ArchiveBench could not start: {error}", file=sys.stderr)
        if sys.stdin.isatty():
            input("Press Enter to close")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
