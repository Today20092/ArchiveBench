# Terminal interface options

Research date: 2026-10-14. Scope: an interactive archival front end over the existing Python engine, not another encoder implementation. Documentation was retrieved through Context7 and checked against upstream source metadata. No dependency was installed or changed during this research.

## Recommendation

Use **Textual** for a small archival TUI. This is a design judgment: the requested editable source selection, preset details, persistent progress and resume view fit an application with widgets better than a sequence of prompts. Keep the existing noninteractive CLI and saved jobs as the execution contract. Do not add AutoHotkey as a dependency.

| Option | Relevant upstream capabilities | ArchiveBench fit and cost |
| --- | --- | --- |
| Textual (MIT) | Multi-value `SelectionList`, `DirectoryTree` file events, asynchronous/thread workers, headless `run_test` with Pilot keyboard/mouse interaction. | Best fit for one persistent source/preset/plan/progress interface. Requires learning its event model and layout; built-in file tree is not a complete multi-root selection policy. |
| prompt_toolkit (BSD-3-Clause) | Full-screen applications, checkbox dialogs, `run_async`, platform-specific pipe input plus `DummyOutput` for tests. | Strong alternative for a deliberately small keyboard wizard. More application layout/state wiring is our responsibility. |
| Questionary (MIT) + Rich (MIT) | Questionary offers checkbox selection, path completion, async prompts and cancellation; Rich provides multi-task progress and live rendering. | Smallest choice for sequential questions followed by progress. Less suited to revisiting selections while a persistent dashboard is visible. Adds two direct libraries and Questionary already depends on prompt_toolkit. Rich alone is an output renderer, not the requested selection application. |

Sources: [Textual widgets](https://github.com/Textualize/textual/blob/main/docs/widget_gallery.md), [DirectoryTree](https://github.com/Textualize/textual/blob/main/docs/widgets/directory_tree.md), [Textual workers](https://github.com/Textualize/textual/blob/main/docs/guide/workers.md), [Textual testing](https://github.com/Textualize/textual/blob/main/docs/guide/testing.md), [prompt_toolkit full-screen apps](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/docs/pages/full_screen_apps.rst), [dialogs](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/docs/pages/dialogs.rst), [asyncio](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/docs/pages/advanced_topics/asyncio.rst), [testing](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/docs/pages/advanced_topics/unit_testing.rst), [Questionary prompt types](https://github.com/tmbo/questionary/blob/master/docs/pages/types.rst), [async prompts](https://github.com/tmbo/questionary/blob/master/docs/pages/advanced.rst), [Rich progress](https://github.com/Textualize/rich/blob/main/docs/source/progress.rst).

## Compatibility and licensing

All four upstream Python requirements admit Python 3.11. At research time, main-branch metadata declares Textual Python 3.9+, prompt_toolkit 3.10+, Questionary 3.10+, and Rich 3.9+. These are source snapshots, not a proposed dependency lock. Resolve and pin a released version when implementation starts. Older indexed Rich documentation still says 3.8+, so current metadata is the stronger source for that requirement.

Textual documents Windows, Linux and macOS support; Rich lists those platforms too. prompt_toolkit identifies OS independence and provides both Windows and POSIX test-input implementations. Questionary builds on prompt_toolkit; actual ArchiveBench behavior on all three operating systems still needs testing. A portable framework does not establish portable FFmpeg termination, path handling, GPU support or launcher behavior.

Sources: [Textual metadata and MIT license declaration](https://github.com/Textualize/textual/blob/main/pyproject.toml), [Textual platforms](https://github.com/Textualize/textual/blob/main/docs/getting_started.md), [prompt_toolkit metadata](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/pyproject.toml), [BSD-3-Clause license](https://github.com/prompt-toolkit/python-prompt-toolkit/blob/main/LICENSE), [Questionary metadata and MIT license declaration](https://github.com/tmbo/questionary/blob/master/pyproject.toml), [Rich metadata and MIT license declaration](https://github.com/Textualize/rich/blob/main/pyproject.toml).

## Minimal first deliverable

1. Open with zero or multiple file/folder arguments. Add paths inside the TUI, deduplicate overlaps, display source-relative destinations, and toggle clips. Reuse existing selection and job validation.
2. Select a saved preset and show codec, CPU/GPU, chroma, audio, container and destination explicitly. Review preflight before starting.
3. Run the existing job engine away from the UI event loop. Present structured progress, failures and durable log location. Persist the exact job before encoding; resume by that job rather than rediscovering a changed selection.
4. Provide a safe stop and resume path. Textual cancellation is not FFmpeg cancellation: threaded workers must cooperate, and subprocess lifecycle handling must explicitly stop/wait for the owned process tree. Do not claim stopped until the process is gone. The [worker guide](https://github.com/Textualize/textual/blob/main/docs/guide/workers.md) explicitly distinguishes thread cancellation from coroutine cancellation.
5. Test headlessly with Pilot: mixed paths, overlapping selections, duplicate basenames, cancellation before launch, responsive progress, interruption/resume, and validation failures. Add real terminal smoke tests on Windows before switching its shortcuts; Linux/macOS claims remain provisional until exercised.

Leave benchmark configuration, charts and video playback in their existing CLI/agent/HTML/native-review routes for the first deliverable. Keep cleanup separate and retain all existing acceptance and integrity gates.

## Windows launch boundary

The reported Explorer Send to failure remains independent and unresolved. A new TUI framework cannot prove or fix the shortcut argument/terminal-host chain. First verify a direct installed console entry point from an existing terminal, then test Explorer with spaces, multiple paths, persistent errors and logging. Do not use PowerShell or AutoHotkey as a required runtime for the TUI. Keep the current working entry points until the replacement is actually verified.

## Limits

This is a primary-source design comparison, not a performance benchmark or prototype. No terminal interaction, package installation, FFmpeg job, source deletion or cross-platform runtime validation was performed for this note.
