"""Interactive archival front end over immutable archive jobs."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import webbrowser
from pathlib import Path

from rich.text import Text

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.theme import Theme
from textual.widgets import (
    Button,
    Checkbox,
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

from .acceptance import inspect_acceptance, record_acceptance
from .archive import cleanup
from .core import save, validate_config
from .experiments import experiment_plan, fixed_settings
from .encoders import SPECS
from .jobs import validate_job
from .presets import resolve_settings, starter_paths
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
        self.deletion_preview = None
        self.reviewed = False
        self.busy = False
        self.process: asyncio.subprocess.Process | None = None
        self.stop_pending = False
        self.quit_pending = False
        self.default_output = ""
        self.preset_paths = [*sorted(self.library.glob("*.json")), *starter_paths()]
        self.preset_rates: dict[str, float | None] = {}
        self.durations: dict[str, float | None] = {}
        self.comparison_config: Path | None = None
        self.comparison_hash = ""

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
            with TabPane("Setup / compare", id="step-setup"), VerticalScroll():
                yield Label("FIRST USE", classes="section-title")
                yield Static(
                    "Recommended: compare representative clips, explore the report and export a measured starting preset. "
                    "For immediate use, continue to Settings and choose a built-in starter; no benchmark is required.",
                    classes="hint",
                )
                yield Select(
                    [
                        ("Recommended: compare encoders", "compare"),
                        ("Optional: short check of selected preset", "sample"),
                    ],
                    value="compare",
                    allow_blank=False,
                    id="comparison-kind",
                )
                yield Label("Total wall-clock allowance (minutes, including scoring and report)")
                yield Input(value="30", id="comparison-minutes")
                yield Label("New comparison output folder (keep outside selected source folders)")
                yield Input(
                    placeholder="Choose a new folder for this comparison", id="comparison-output"
                )
                with Collapsible(title="Comparison sections and encoders", collapsed=True):
                    yield Static(
                        "Uses every selected clip. Select representative clips in Clips first."
                    )
                    yield Label("Section start / length in seconds (same interval per clip)")
                    yield Input(value="0", id="comparison-offset")
                    yield Input(value="5", id="comparison-length")
                    yield Label(
                        "Comparison encoders (sample check uses the selected preset instead)"
                    )
                    yield Input(value="libx265,libsvtav1,hevc_nvenc", id="comparison-encoders")
                yield Button("Review comparison settings", id="comparison-review")
                yield Static(
                    "Review before starting. No encoding has started.",
                    id="comparison-brief",
                    markup=False,
                )
                yield Button("Start reviewed comparison", id="comparison-start", disabled=True)
                yield Button(
                    "Open completed report / export preset", id="comparison-report", disabled=True
                )
                yield Label("Load the preset JSON exported by the report")
                yield Input(placeholder="Exported preset path", id="import-preset")
                yield Button("Use exported preset", id="import-preset-button")
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
                with Collapsible(title="Technical settings", id="preset-technical", collapsed=True):
                    yield Static("Choose a preset first.", id="preset-details", markup=False)
                yield Static(
                    "Historical measurements do not validate these clips. Output size is unknown without measurements. "
                    "Optional sampling is in Setup / compare; estimates exclude retained streams, verification and untested footage.",
                    id="scope-summary",
                    markup=False,
                )
                yield Checkbox(
                    "Accept uncertain suitability for these clips (sampling optional)",
                    id="scope-accept",
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
            with TabPane("5 Accept / cleanup", id="step-cleanup"), VerticalScroll():
                yield Static(
                    "After processing ends, optionally spot-check outputs or reopen an editor copy. "
                    "Actual visual/editor reviews can be recorded with the acceptance command. "
                    "You may instead explicitly accept the preset's quality tradeoff without inspection. "
                    "Neither processing nor acceptance authorizes deletion.",
                    classes="hint",
                )
                yield Input(placeholder="Your name", id="acceptance-name")
                yield Input(placeholder="Why you accept the quality tradeoff", id="acceptance-note")
                yield Button("Accept quality tradeoff without inspection", id="accept-tradeoff")
                yield Button("Preview original deletion", id="preview-deletion")
                yield Static(
                    "No deletion preview. Originals remain intact.",
                    id="deletion-preview",
                    markup=False,
                )
                yield Button(
                    "Approve permanent deletion of previewed originals",
                    id="delete-originals",
                    disabled=True,
                    variant="warning",
                )
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
            name = path.stem
            try:
                document = json.loads(path.read_text(encoding="utf-8"))
                facts = preset_facts(resolve_settings(document))
                name = document.get("name", name)
                self.preset_rates[str(path)] = measured_rate(document)
            except (OSError, ValueError, KeyError):
                facts = ("Invalid preset", "-", "-", "-", "-")
            cells = [Text(str(value)) for value in facts]
            cells[1].stylize({"CPU": "bold #ddd6fe", "GPU": "bold #fde68a"}.get(facts[1], ""))
            table.add_row(Text(name), *cells[:3], "Select clips", *cells[3:], key=str(path))
        table.cursor_foreground_priority = "renderable"
        self.query_one("#aac-options").display = False
        if self.sources:
            self.scan(self.sources)

    def invalidate(self):
        self.deletion_preview = None
        self.query_one("#delete-originals", Button).disabled = True
        self.query_one("#deletion-preview", Static).update(
            "No current deletion preview. Preview again before approval."
        )
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
            self.query_one("#comparison-start", Button).disabled = True
            self.invalidate()

    def on_selection_list_selected_changed(self):
        self.query_one("#comparison-start", Button).disabled = True
        self.query_one("#scope-accept", Checkbox).value = False
        self.refresh_estimates()
        if not self.busy:
            self.invalidate()

    def on_checkbox_changed(self, event: Checkbox.Changed):
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
        self.query_one("#comparison-start", Button).disabled = True
        self.query_one("#aac-options").display = self.query_one("#audio", Select).value == "aac"
        if event.select.id == "preset" and isinstance(event.value, str):
            self.query_one("#scope-accept", Checkbox).value = False
            try:
                document = json.loads(Path(event.value).read_text(encoding="utf-8"))
                settings = resolve_settings(document)
                self.query_one("#scope-summary", Static).update(
                    "Historical footage scope: "
                    + json.dumps(document.get("scope", {}).get("footage", []), ensure_ascii=False)
                    + "\nEvidence: "
                    + str(document.get("evidence", {}).get("measurement_status", "unknown"))
                    + ". Current clips are unvalidated; output size is unknown. Optional sample in Setup / compare. "
                    "Sample estimates are approximate and exclude retained streams, verification and untested footage."
                )
                self.query_one("#summary", Static).update(
                    f"SELECTED: {document.get('name', Path(event.value).stem)}\n"
                    f"{document.get('description', preset_description(settings))}"
                )
                self.query_one("#preset-details", Static).update(
                    f"{preset_description(settings)}\nEncoder: {settings['encoder']}\n"
                    "Source frame rate retained. Audio policy is selected below.\n"
                    + (
                        "Actual pixel format matches each source clip; incompatible formats are rejected.\n"
                        "Stored encoder controls below: yuv420p is a template placeholder.\n"
                        if settings["pixel_format"] == "source"
                        else "Encoder controls:\n"
                    )
                    + " ".join(document.get("encoder_options", []))
                )
            except (OSError, ValueError) as error:
                self.error(error)

    def error(self, error):
        self.query_one("#status", Static).update(f"Error: {error}")
        self.query_one("#log", RichLog).write(str(error))

    def set_busy(self, value: bool):
        self.busy = value
        for widget in self.query("Input, Select, SelectionList, Checkbox"):
            widget.disabled = value
        for name in ("add", "all", "none", "review", "accept-tradeoff", "preview-deletion"):
            self.query_one(f"#{name}", Button).disabled = value
        self.query_one("#delete-originals", Button).disabled = value or not self.deletion_preview
        self.query_one("#preset-table", DataTable).disabled = value
        self.query_one("#stop", Button).disabled = not value
        self.query_one("#start", Button).disabled = value or not self.reviewed
        for name in ("comparison-review", "import-preset-button"):
            self.query_one(f"#{name}", Button).disabled = value

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
            steps = tuple(pane.id for pane in self.query(TabPane))
            tabs.active = steps[
                max(
                    0,
                    min(len(steps) - 1, steps.index(tabs.active) + (1 if action == "next" else -1)),
                )
            ]
        elif action == "comparison-review":
            self.review_comparison()
        elif action == "comparison-start":
            self.run_comparison()
        elif action == "comparison-report" and self.comparison_config:
            webbrowser.open((self.comparison_config.parent / "report.html").as_uri())
        elif action == "import-preset-button":
            try:
                path = Path(
                    self.query_one("#import-preset", Input).value.strip().strip('"')
                ).resolve()
                document = json.loads(path.read_text(encoding="utf-8"))
                settings = resolve_settings(document)
                if path not in self.preset_paths:
                    self.preset_paths.append(path)
                    self.preset_rates[str(path)] = measured_rate(document)
                    facts = preset_facts(settings)
                    self.query_one("#preset-table", DataTable).add_row(
                        Text(document.get("name", path.stem)),
                        *facts[:3],
                        "No timing data",
                        *facts[3:],
                        key=str(path),
                    )
                    self.query_one("#preset", Select).set_options(
                        [(p.stem, str(p)) for p in self.preset_paths]
                    )
                self.query_one("#preset", Select).value = str(path)
                self.set_focus(None)
                self.query_one(TabbedContent).active = "step-settings"
            except (OSError, ValueError) as error:
                self.error(error)
        elif action in ("accept-tradeoff", "preview-deletion", "delete-originals"):
            self.postjob(action)
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

    @work(exclusive=True, group="postjob")
    async def postjob(self, action: str):
        if self.busy:
            return
        preview = self.deletion_preview
        self.deletion_preview = None
        self.set_busy(True)
        try:
            saved = self.query_one("#saved-job", Input).value.strip().strip('"')
            path = Path(saved) if saved else self.job_path
            if path is None:
                raise ValueError("Load or finish a saved job first")
            job = json.loads(path.read_text(encoding="utf-8"))
            validate_job(job)
            root = Path(job["output_root"])
            if (root / ".lock").exists():
                raise ValueError("Job is still active; wait before acceptance or cleanup")
            if action == "accept-tradeoff":
                await asyncio.to_thread(
                    record_acceptance,
                    root,
                    "quality-tradeoff",
                    "accept",
                    self.query_one("#acceptance-name", Input).value,
                    note=self.query_one("#acceptance-note", Input).value,
                )
                self.query_one("#deletion-preview", Static).update(
                    "Quality tradeoff accepted without visual/editor inspection. Originals retained. Preview deletion separately."
                )
            else:
                state = await asyncio.to_thread(inspect_acceptance, root)
                if action == "delete-originals":
                    if not preview or preview != (
                        str(root),
                        state["binding"],
                        state["eligible"],
                        state["attestations"],
                    ):
                        raise ValueError("Deletion preview missing or changed; preview again")
                    await asyncio.to_thread(
                        cleanup,
                        root,
                        True,
                        True,
                        selected_sources=[item["source"] for item in state["eligible"]],
                    )
                    self.query_one("#deletion-preview", Static).update(
                        "Approved originals deleted. Archived outputs retained."
                    )
                elif state["eligible"]:
                    self.deletion_preview = (
                        str(root),
                        state["binding"],
                        state["eligible"],
                        state["attestations"],
                    )
                    self.query_one("#deletion-preview", Static).update(
                        "Permanent deletion preview (approval applies only to these originals):\n"
                        + "\n".join(item["source"] for item in state["eligible"])
                    )
                else:
                    raise ValueError(
                        "No currently accepted verified replacements eligible for deletion"
                    )
        except (ValueError, OSError) as error:
            self.error(error)
        finally:
            self.set_busy(False)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if not self.busy and event.row_key.value is not None:
            self.query_one("#preset", Select).value = event.row_key.value

    def review_comparison(self):
        try:
            selected = self.query_one("#clips", SelectionList).selected
            if not selected:
                raise ValueError("Select representative clips first")
            output_text = self.query_one("#comparison-output", Input).value.strip().strip('"')
            if not output_text:
                raise ValueError("Choose a new comparison output folder")
            output = Path(output_text).resolve()
            if (output / "results.json").exists():
                raise ValueError("Comparison already started; choose a new output folder")
            start = float(self.query_one("#comparison-offset", Input).value)
            seconds = float(self.query_one("#comparison-length", Input).value)
            samples = []
            for path in selected:
                duration = self.durations.get(path)
                if duration is None:
                    raise ValueError("Wait for clip durations before comparison review")
                if start < 0 or seconds <= 0 or start + seconds > duration:
                    raise ValueError("Section must fit every selected clip")
                samples.append(
                    {"path": path, "label": Path(path).name, "start": start, "seconds": seconds}
                )
            sample = self.query_one("#comparison-kind", Select).value == "sample"
            settings = {}
            if sample:
                preset = self.query_one("#preset", Select).value
                if not isinstance(preset, str):
                    raise ValueError("Choose a preset in Settings before sampling")
                settings = resolve_settings(json.loads(Path(preset).read_text(encoding="utf-8")))
            encoders = (
                [settings["encoder"]]
                if sample
                else [
                    item.strip()
                    for item in self.query_one("#comparison-encoders", Input).value.split(",")
                ]
            )
            config = {
                "version": 1,
                "strategy": "fixed",
                "profile": "compact",
                "mode": "quick",
                "encode_repeats": 1,
                "pixel_format": settings.get("pixel_format", "source"),
                "resolution": settings.get("resolution", "original"),
                "audio_mode": "copy",
                "budget_minutes": float(self.query_one("#comparison-minutes", Input).value),
                "samples": samples,
                "encoders": encoders,
            }
            if sample:
                config["fixed_settings"] = {settings["encoder"]: [settings["quality"]]}
            config["fixed_settings"] = fixed_settings(config)
            validate_config(config)
            if any(Path(path).resolve().is_relative_to(output) for path in selected):
                raise ValueError("Comparison output cannot contain a selected source")
            config_path = output / "config.json"
            if config_path.exists() and config_path != self.comparison_config:
                raise ValueError(
                    "Comparison folder has an existing configuration; choose a new folder"
                )
            self.comparison_config = config_path
            save(self.comparison_config, config)
            self.comparison_hash = hashlib.sha256(self.comparison_config.read_bytes()).hexdigest()
            self.query_one("#comparison-brief", Static).update(
                json.dumps(experiment_plan(config), indent=2)
                + "\nOriginals retained. Video-only sample; no fresh validation or visual acceptance. "
                "Size/time extrapolation is approximate; excludes retained streams, verification, untested footage. "
                "Incomplete/failed trials remain visible in the report. Review these exact choices before Start."
            )
            self.query_one("#comparison-start", Button).disabled = False
        except (OSError, ValueError) as error:
            self.error(error)

    @work(exclusive=True, group="comparison")
    async def run_comparison(self):
        if self.busy or self.comparison_config is None:
            return
        self.set_busy(True)
        self.stop_pending = False
        self.query_one("#comparison-start", Button).disabled = True
        self.query_one("#comparison-report", Button).disabled = True
        self.query_one(TabbedContent).active = "step-progress"
        try:
            if (
                hashlib.sha256(self.comparison_config.read_bytes()).hexdigest()
                != self.comparison_hash
            ):
                raise ValueError("Comparison settings changed; review again")
            self.process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-u",
                "-m",
                "archivebench.tui_worker",
                str(self.comparison_config),
                "--comparison",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            assert self.process.stdout is not None
            if self.stop_pending:
                self.request_stop()
            async for line in self.process.stdout:
                self.query_one("#log", RichLog).write(
                    line.decode("utf-8", errors="replace").rstrip()
                )
            code = await self.process.wait()
            report = self.comparison_config.parent / "report.html"
            self.query_one("#comparison-report", Button).disabled = not report.exists()
            self.query_one("#status", Static).update(
                f"Comparison {'finished' if code == 0 else 'stopped or failed'}. "
                "Return to Setup / compare, open the report, inspect missing/failed evidence, export a preset and load it here. "
                "Short measurements do not validate all footage."
            )
        except (OSError, ValueError) as error:
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
                if not self.query_one("#scope-accept", Checkbox).value:
                    raise ValueError(
                        "Accept uncertain preset suitability in Settings, or run an optional comparison first"
                    )
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
                path = Path(job["output_root"]) / "archive-job.json"
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
        self.deletion_preview = None
        self.set_busy(True)
        self.query_one(TabbedContent).active = "step-progress"
        self.stop_pending = False
        try:
            if hashlib.sha256(self.job_path.read_bytes()).hexdigest() != self.job_hash:
                raise ValueError("Saved job changed; review it again")
            snapshot = json.loads(self.job_path.read_text(encoding="utf-8"))
            log_path = Path(snapshot["output_root"]) / "archive-job.json.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
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
                else "Processing finished. Check failed / kept-original records. Continue to Accept / cleanup for optional review or quality-tradeoff acceptance, then separate deletion approval."
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
