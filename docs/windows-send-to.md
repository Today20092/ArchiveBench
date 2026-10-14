# Windows Send to launcher

[Back to the README](../README.md#windows-send-to) · [Archive jobs](archiving.md)

This optional per-user launcher calls the installed `archivebench` CLI. It selects a saved preset and creates or resumes a project job; it does not run a benchmark or cleanup. Install the current revision using [installation](installation.md); older releases may lack `archivebench-send-to`.

```powershell
archivebench-send-to --install --preset-directory "D:\Archive Presets"
```

From a source checkout, the installer is also available as `uv run archivebench-send-to --install --preset-directory "D:\Archive Presets"`. An installed `archivebench` command must be on PATH for use outside that checkout. Without a directory argument, the preset library is `ArchiveBench Presets` under your Windows Documents folder. The installer creates it if missing; export your approved JSON presets there.

To install or update the persistent commands from this checkout, first finish any running ArchiveBench jobs, then run:

```powershell
uv tool install --python 3.11 --force .
uv tool update-shell
```

Open a new terminal if needed for PATH changes. Updating the tool is separate from installing the shortcut; the shortcut installer does not replace your runner.

The installer copies the launcher to `%LOCALAPPDATA%\ArchiveBench\SendTo` and adds `ArchiveBench.lnk` to your Windows SendTo folder. The shortcut targets Windows PowerShell directly, so folder arguments are not interpolated into a batch command. Installation does not grant broader permissions or bypass PowerShell execution policy. If your policy blocks scripts, follow your organization's approved script-signing policy or use the terminal workflow. Keep FFmpeg/ffprobe and the current CLI on PATH.

Right-click one footage folder, choose **Send to → ArchiveBench**, select a numbered preset, inspect preflight, and type `ARCHIVE`. Anything else cancels encoding. Empty preset selection cancels without creating a job. Errors stay visible in the console. Multiple folders and individual files are rejected; send one folder at a time.

The default output is `<source>-Archived-<preset-filename>` with an adjacent `<output>.job.json`. Repeating the same selection resumes that exact job: verified files are skipped, pending/interrupted files start again. The launcher refuses different settings under an existing job; save the changed preset with a different filename or choose another output through the terminal/script. It never changes an existing job's saved preset snapshot. Prepare any keep-original/stronger-setting exceptions through the regular CLI before the job's first encode; do not change an existing execution snapshot.

For a custom destination or inspection only, invoke the copied PowerShell script with `-SourcePath`, `-Preset`, `-OutputPath` and optionally `-InspectOnly`. Inspection performs short scratch probes. Output verification, source hashes, actual savings and full decode checks remain in the shared runner. Successful encoding is separate from visual/editor acceptance and never removes originals.

To remove the integration, open `shell:sendto` in Explorer and delete only `ArchiveBench.lnk`; remove its copied `archivebench-send-to.ps1` from `%LOCALAPPDATA%\ArchiveBench\SendTo` if no longer needed. Presets, jobs, archives and originals are unaffected. Rerun the installer to refresh the generated shortcut/launcher after an update.

Windows checks cover actual shortcut creation/target arguments and scripted console selection, synthetic encode, resume and cancellation, including spaces and metacharacters in paths. The interactive Explorer menu click still needs a human smoke check. No real-camera quality acceptance is inferred from these tests.
