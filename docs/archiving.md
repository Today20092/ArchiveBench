# Archive files and review cleanup

Reusable jobs enforce explicit suitability consent outside a preset's historical footage scope. Run `archivebench job inspect JOB.json` first. If it reports `acceptance-required`, explicitly accept that uncertainty with `archivebench job inspect JOB.json --accept-uncertain-suitability`, then use `archivebench job run JOB.json --execute`. The TUI Settings checkbox records the same decision for new and saved jobs. This consent is separate from actual visual/editor review, replacement acceptance and deletion approval.

The consent-only `suitability-acceptance.json` records the immutable job, probed footage characteristics, source sizes and modification times; changes invalidate it. This is a stat/probe binding, not a content-hash attestation. Original/archive integrity and cleanup still require their existing hash checks. The manifest and offline summary record the executed suitability decision. Old saved jobs require an explicit decision when none is recorded.

Rejected preflights probe up to four bundled alternatives on the selected footage (one frame per file, 30 seconds per probe). CLI plans and TUI Settings report passed candidates and failed candidates/reasons. Choose an alternative explicitly, review its exact settings and policies and preflight a new job; the current job is never changed automatically. Quality and size/time remain untested/unknown. CLI `job create` also discovers destination jobs: matching selections/settings resume their saved snapshot, while conflicts explain which choices must be resumed or moved to another destination.

Use [the terminal UI](terminal-ui.md) to select clips, choose a destination and preset, review output policies, and run or resume a job. [Windows Send to](windows-send-to.md) opens the same UI. The [legacy desktop workflow](archive-desktop.md) remains available, including the separate cleanup selector. Existing presets without a container still default to MKV; the text below describes those defaults.

For reusable folder jobs, follow [editor reopening and replacement acceptance](editor-acceptance.md). The job workflow requires an identity-bound replacement decision: actual visual/editor attestations or explicit quality-tradeoff acceptance without inspection, followed by separate cleanup approval after processing ends. Legacy manifests keep their existing documented handling.

## Reusable project jobs

Once you have chosen presets, use these jobs on future folders without repeating the benchmark. The optional [Windows Send to launcher](windows-send-to.md) performs the same operation through Explorer.

The installed runner accepts any source and destination folders. A portable preset contains
settings and historical evidence; a local job contains folder paths, an embedded preset snapshot
and explicit file exceptions. Editing the original preset does not change an existing job.

```powershell
archivebench job create project-job.json --source footage --output archive-output --preset accepted-preset.json
archivebench job inspect project-job.json
# If required, only after explicitly accepting uncertain suitability:
archivebench job inspect project-job.json --accept-uncertain-suitability
archivebench job run project-job.json --execute
```

Run without `--execute` to inspect first. Preflight lists source/destination mappings, resolved
settings, unsupported preservation cases, a scratch planning allowance and historical video-only
estimates when the preset supplies measured byte/time rates. Unknown estimates remain unknown;
retained streams and verification time are excluded. Short encode/mux probes run before full
encoding. A successful probe does not certify editor compatibility or proprietary metadata.
Data streams, cover art and multiple video streams without a tested preservation path
produce a keep-original outcome. Originals remain intact.

Optional `--exceptions exceptions.json` on `job create` accepts a JSON list:

```json
[
  {"path": "night/important.mov", "action": "keep-original"},
  {"path": "interview/detail.mov", "action": "stronger-setting", "preset": "stronger-preset.json"}
]
```

Paths identify exact eligible files relative to the source root; traversal, duplicates and
unmatched exceptions are rejected. Stronger settings preserve the same encoder/video/retention
policy and request higher quality. Overrides are explicit, never selected automatically.
Create another job with another source/output pair to reuse the same preset for a second project.
Each output has its own `archive-manifest.json`. Resume checks the job snapshot, source hashes,
completed output hashes and settings. Keep-original files are excluded from encoding and cleanup;
files without useful actual savings retain their originals and are recorded as not worth encoding.
New workflow jobs require current replacement acceptance before separate cleanup. Timecode follows the explicit preserve/reject/drop job policy: preservation requires supported MOV/MP4 and verification; reject blocks timecoded input; drop explicitly removes timecode.

[Back to the README](../README.md) · [Configuration and retention options](configuration.md)

## Review the settings

Select a measured configuration in the report and click **Export archive settings**. Optionally inspect the saved clips at native size and test grading or editing needs; alternatively explicitly accept the quality tradeoff without claiming inspection.

The exported settings carry the video format, resolution and retention choices selected during setup. Audio and other streams are excluded from benchmark size/time measurements. The runner writes MKV. It cannot guarantee proprietary metadata or editor relinking; test that compatibility separately.

The [configuration reference](configuration.md) describes retention defaults, optional AAC conversion and track removal, supported streams, verification and version 1 manifest behavior. Unsupported streams stop the job rather than being silently omitted.

## Encode a batch

First review the eligible files and settings. This command does not encode:

```powershell
uv run archivebench archive --source D:\Project\Originals --output E:\Project\Archived --settings archive-settings.json
```

After reviewing that list, explicitly execute the batch:

```powershell
uv run archivebench archive --source D:\Project\Originals --output E:\Project\Archived --settings archive-settings.json --execute
```

Originals remain in place. The runner validates outputs before marking them verified. Encodes saving less than 10% are discarded; originals stay intact. A batch failure stops the run and leaves its checkpoint for inspection or restart. Rerun with the same source, output and settings to continue. See [lock-file handling](benchmark.md#restart-and-budgets) after an abrupt shutdown.

## Run an overnight archive next to Originals

The existing runner can handle a full project after you choose and review benchmark settings. Use a neighboring `Archived` directory as the output:

```powershell
uv run archivebench archive --source D:\Project\Originals --output D:\Project\Archived --settings archive-settings.json
uv run archivebench archive --source D:\Project\Originals --output D:\Project\Archived --settings archive-settings.json --execute
```

The first command reviews the list; the second encodes it. Leave the computer awake with enough output space. Relative subfolders are retained, and outputs have an `.archive.mkv` suffix. You can choose another disk instead by changing `--output`.

If using the installed command, omit `uv run`. An agent can adapt the runner for your project, but it should keep the saved settings, checkpoint, hash/path/stream/decode checks and separate cleanup. A convenience scheduling wrapper is a possible future addition; the current runner executes when launched.

## Review and remove originals

**Cleanup permanently deletes the listed originals.** For new jobs, run it only after processing ends, current replacement acceptance and an explicit decision to remove the previewed files. Benchmarking or encoding alone is not permission to delete them.

Preview the cleanup list first:

```powershell
uv run archivebench cleanup --output E:\Project\Archived
```

Only after current replacement acceptance and approval of the exact list:

```powershell
uv run archivebench cleanup --output E:\Project\Archived --execute --reviewed
```

Cleanup requires matching source/output hashes, at least 10% actual savings, audio/video and retention validation, and full decode checks. It validates the whole selection before deleting any original and rechecks hashes before each deletion. The archive runner never deletes originals while encoding.

For immediate use without a benchmark, see [starter presets and job outcomes](terminal-workflow.md#immediate-use-and-job-outcomes). The TUI offers built-in starters and explains uncertain scope, optional sampling, destination resume and the offline job summary. Visual/editor review is optional; explicit quality-tradeoff acceptance records a different decision and never asserts inspection.
