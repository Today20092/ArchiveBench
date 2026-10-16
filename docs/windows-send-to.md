# Windows Send to launcher

[Back to the README](../README.md#windows-send-to) · [Terminal UI](terminal-ui.md) · [Archive jobs](archiving.md)

Select folders, clips or a mixture in Explorer, then choose **Send to > Archive footage**. Windows 11 may require **Show more options** first. Send to passes those sources to ArchiveBench. Choose the output folder inside the TUI, review preflight and press Start. It does not start a benchmark or delete originals.

## Install or update

The TUI workflow is included in v0.2.0. Finish running ArchiveBench jobs before installing or replacing the tool:

```powershell
uv tool install --python 3.11 --force https://github.com/Today20092/ArchiveBench/releases/download/v0.2.0/archivebench-0.2.0-py3-none-any.whl
uv tool update-shell
```

Open a new terminal if PATH changed, then install or refresh the shortcuts:

```powershell
archivebench-send-to --install --preset-directory "D:\Archive Presets"
```

Updating the installed tool and refreshing the shortcuts are separate operations. Keep FFmpeg, ffprobe and ArchiveBench on PATH. Without a preset-directory argument, the installer uses `ArchiveBench Presets` under your Windows Documents folder and creates it if missing. Export your chosen JSON presets there.

The installer creates these per-user shortcuts:

| Shortcut | Current behavior |
| --- | --- |
| Archive footage | Opens the TUI with the selected sources. |
| Archive footage (terminal) | Opens the same TUI. The older name is retained. |
| Review originals for deletion | Opens the separate legacy cleanup selector for one archive folder, with acceptance and verification checks. |

Both archive shortcuts launch `archivebench-tui` directly through the Windows console host. They do not need a PowerShell runtime wrapper. PowerShell is still used by the installer and cleanup launcher. Installation does not bypass execution policy.

The default console shortcut fits its dedicated window to the monitor work area. Ordinary `archivebench-tui` commands keep the existing terminal size. To use an installed WezTerm instead:

```powershell
archivebench-send-to --install --terminal wezterm --preset-directory "D:\Archive Presets"
```

WezTerm keeps your normal configuration. Use `--terminal conhost` to restore the default host.

## Select a destination and resume

Sources must share one drive; the output may be on another drive. Overlapping selections are deduplicated and relative paths beneath the common source folder are preserved. The TUI proposes `Archived Footage` under that folder. A directly selected `Original Footage` folder gets a sibling `Archived Footage` destination. Review the proposed destination when combining unrelated folders.

Choose a preset and destination in Settings, then run preflight in Review. Start becomes available after successful preflight. The saved job holds the selected files and settings; the log is beside it. Resume that exact job:

```powershell
archivebench-tui --job "D:\Project\Archived Footage.job.json"
```

Completed files must still pass identity checks. An interrupted file restarts from its beginning. Different selections or settings cannot silently replace an existing job. Use a different destination for another preset version. See [the TUI guide](terminal-ui.md) for safe stopping and [archive verification](archiving.md) for acceptance and cleanup.

## Legacy launchers

The packaged `windows/install-send-to.ps1` script accepts `-Legacy`. This is a script option, not an `archivebench-send-to` CLI option. It restores the older Tkinter selector for **Archive footage** and numbered prompts for **Archive footage (terminal)**. The latter accepts one folder, asks for a preset and requires typing `ARCHIVE` after preflight.

The legacy numbered launcher defaults to `<source>-Archived-<preset-filename>` with an adjacent `.job.json`. Its copied PowerShell script accepts `-SourcePath`, `-Preset`, `-OutputPath` and `-InspectOnly`. These defaults and prompts do not describe the current TUI. See [the legacy desktop guide](archive-desktop.md).

## Remove the shortcuts

Open `shell:sendto` in Explorer and delete the three named shortcuts. Copied scripts under `%LOCALAPPDATA%\ArchiveBench\SendTo` can also be removed if no longer needed. Presets, jobs, archives and originals are unaffected. The installer removes older `ArchiveBench`, `ArchiveBench Desktop` and `ArchiveBench Cleanup` shortcut names when updating.

Automated shortcut and terminal checks do not establish that Explorer launching works on every installation. Verify an actual Explorer selection separately. Synthetic encode tests do not establish camera-footage quality or editor acceptance.
