# Archive files and review cleanup

## Reusable project jobs

The installed runner accepts any source and destination folders. A portable preset contains
settings and historical evidence; a local job contains folder paths, an embedded preset snapshot
and explicit file exceptions. Editing the original preset does not change an existing job.

```powershell
archivebench job create project-job.json --source footage --output archive-output --preset accepted-preset.json
archivebench job inspect project-job.json
archivebench job run project-job.json --execute
```

Run without `--execute` to inspect first. Preflight lists source/destination mappings, resolved
settings, unsupported preservation cases, a scratch planning allowance and historical video-only
estimates when the preset supplies measured byte/time rates. Unknown estimates remain unknown;
retained streams and verification time are excluded. Short encode/mux probes run before full
encoding. A successful probe does not certify editor compatibility or proprietary metadata.
Data/timecode streams, cover art and multiple video streams without a tested preservation path
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
New workflow jobs require recorded visual/editor acceptance before separate cleanup.

[Back to the README](../README.md) · [Configuration and retention options](configuration.md)

## Review the settings

Select a measured configuration in the report and click **Export archive settings**. Inspect the saved clips at native size and test any grading or editing workflow you need before running a full batch.

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

**Cleanup permanently deletes the listed originals.** Run it only after visual review and an explicit decision to remove those files. Benchmarking or encoding alone is not permission to delete them.

Preview the cleanup list first:

```powershell
uv run archivebench cleanup --output E:\Project\Archived
```

Only after reviewing the encoded clips and the list:

```powershell
uv run archivebench cleanup --output E:\Project\Archived --execute --reviewed
```

Cleanup requires matching source/output hashes, at least 10% actual savings, audio/video and retention validation, and full decode checks. It validates the whole selection before deleting any original and rechecks hashes before each deletion. The archive runner never deletes originals while encoding.
