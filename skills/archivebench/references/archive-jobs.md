# Run a reusable archive

For human-driven archival, launch `archivebench-tui` with optional folder/file arguments and `--preset-directory`. Use `--job JOB.json` to review and resume the exact saved job. Review preflight before Start. Stop waits for owned FFmpeg cleanup or the current verification/preflight operation; completed records remain and interrupted clips restart. Keep the terminal open until stopped. Use the noninteractive CLI below for agent automation. Cleanup remains separate. Do not infer Explorer compatibility from a direct-terminal test.

For interactive Windows selection, use `archivebench-desktop --root PROJECT`. It selects an Original Footage subtree by default, proposes Archived Footage, and exposes explicit MOV/MP4/MKV, audio, data and timecode policies. Review the selected file list and chroma statement. The GUI saves an immutable shared job; preflight and a typed ARCHIVE confirmation precede full encoding. Use the CLI for automation. Desktop jobs display encode progress and continue individual encode/verification failures while preserving originals; identity conflicts and storage problems stop the batch. Legacy Proxy Watcher jobs remain with their old runner.

Use the shared reusable job commands. A job snapshots its preset and keeps paths, exceptions and resume state separate from historical preset evidence:

```powershell
archivebench job create JOB.json --source SOURCE --output DESTINATION --preset PRESET.json
archivebench job inspect JOB.json
archivebench job run JOB.json
archivebench job run JOB.json --execute
```

Create a separate job/output root per project. Inspection runs short scratch encode/mux compatibility probes, but does not run full archive encodes. Execution probes, encodes and verifies; repeating it resumes matching inputs. Use `--exceptions EXCEPTIONS.json` on job creation for a list such as `[{"path":"night/clip.mov","action":"keep-original"}]`. A stronger-setting exception also provides `"preset":"stronger.json"`; only an explicitly stronger setting with the same format/retention policy is allowed. Never silently choose overrides.

The legacy runner writes `.archive.mkv`, rejects unsupported streams and discards encodes below its savings threshold. Check timecode, data streams, sidecars and proprietary metadata before replacement. Container or filename changes can affect project relinking. Unsupported cases keep originals until a tested adaptation exists; a converted video playing successfully does not certify an editing project.

Report actual bytes and savings including retained streams. Run `archivebench acceptance inspect --output DESTINATION` for the mapping and evidence gaps. After actual human review, use `acceptance record --output DESTINATION --kind visual --decision accept --reviewer NAME`. Record the separate editor check with `--kind editor --decision accept --reviewer NAME --editor "NAME VERSION" --project-copy COPY`. Never fabricate attestations. Unsupported editor workflows remain unverified.

Completion: each authorized file has a verified output or an explicit keep-original/failure outcome, and required visual/editor acceptance is recorded separately from automated checks.
