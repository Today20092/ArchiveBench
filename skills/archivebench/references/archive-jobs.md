# Run a reusable archive

For human-driven archival, launch `archivebench-tui` with optional folder/file arguments and `--preset-directory`. Use `--job JOB.json` to review and resume the exact saved job. Review preflight before Start. Stop waits for owned FFmpeg cleanup or the current verification/preflight operation; completed records remain and interrupted clips restart. Keep the terminal open until stopped. Use the noninteractive CLI below for agent automation. Cleanup remains separate. Do not infer Explorer compatibility from a direct-terminal test.

For interactive Windows selection, use `archivebench-desktop --root PROJECT`. It selects an Original Footage subtree by default, proposes Archived Footage, and exposes explicit MOV/MP4/MKV, audio, data and timecode policies. Review the selected file list and chroma statement. The GUI saves an immutable shared job; preflight and a typed ARCHIVE confirmation precede full encoding. Use the CLI for automation. Desktop jobs display encode progress and continue individual encode/verification failures while preserving originals; identity conflicts and storage problems stop the batch. Legacy Proxy Watcher jobs remain with their old runner.

Use the shared reusable job commands. A job snapshots its preset and keeps paths, exceptions and resume state separate from historical preset evidence:

```powershell
archivebench job create JOB.json --source SOURCE --output DESTINATION --preset PRESET.json
archivebench job inspect JOB.json
archivebench job run JOB.json
# Only after the user explicitly accepts uncertain suitability shown by preflight:
archivebench job inspect JOB.json --accept-uncertain-suitability
archivebench job run JOB.json --execute
```

Create a separate job/output root per project. Inspection runs short scratch encode/mux compatibility probes, but does not run full archive encodes. Execution probes, encodes and verifies; repeating it resumes matching inputs. Use `--exceptions EXCEPTIONS.json` on job creation for a list such as `[{"path":"night/clip.mov","action":"keep-original"}]`. A stronger-setting exception also provides `"preset":"stronger.json"`; only an explicitly stronger setting with the same format/retention policy is allowed. Never silently choose overrides.

Creation discovers a saved job at the destination and reuses its immutable snapshot when the source, selected files, settings and exceptions match. Conflicts require resuming the saved choices or choosing another destination. CLI creation selects all eligible files outside the destination; use an existing selection job to resume a subset.

Resume the same saved job after approved cleanup of completed originals. Deleted-original records retain their selection/history and are skipped only after their replacement mapping, settings and hash are checked again; other missing originals or changed/missing replacements refuse resume. Unfinished files still process normally, and prior suitability consent survives only for the unchanged remaining scope.

Preflight reports `suitability.status`. An `acceptance-required` job cannot encode until the user explicitly accepts uncertain suitability: use `--accept-uncertain-suitability` with inspect/run, or the Settings checkbox before reviewing a saved or new job in the TUI. The consent-only `suitability-acceptance.json` binds that decision to the immutable job, actual probed footage characteristics, source sizes and modification times. Changed settings, selection, scope or source identity require a fresh decision; older jobs receive no invented consent. This stat/probe binding is not a content-hash attestation. Archive and cleanup hash verification remains authoritative. The executed decision appears in the manifest and offline summary, separately from visual/editor and replacement/deletion acceptance.

On rejection, preflight also tries up to four bundled alternatives on the selected footage, one frame per file with a 30-second limit per probe. Both passed candidates and failed candidates/reasons appear in the CLI plan and TUI Settings. These are technical compatibility probes; quality and size/time estimates remain untested/unknown. Offer the actual passed choices for explicit selection, then create/review a job with that exact preset and policy and preflight again. Never select, convert or replace the current snapshot automatically. A failed current choice continues to keep originals.

The legacy runner writes `.archive.mkv`, rejects unsupported streams and discards encodes below its savings threshold. Check timecode, data streams, sidecars and proprietary metadata before replacement. Container or filename changes can affect project relinking. Unsupported cases keep originals until a tested adaptation exists; a converted video playing successfully does not certify an editing project.

Report actual bytes and savings including retained streams. Run `archivebench acceptance inspect --output DESTINATION` for the mapping and evidence gaps. For optional actual human review, use `acceptance record --output DESTINATION --kind visual --decision accept --reviewer NAME`. Record the separate editor check with `--kind editor --decision accept --reviewer NAME --editor "NAME VERSION" --project-copy COPY`. Never fabricate attestations. Unsupported editor workflows remain unverified.

Alternatively record the user's explicit decision with `acceptance record --output DESTINATION --kind quality-tradeoff --decision accept --reviewer NAME --note REASON`. This asserts no visual/editor inspection and cannot waive preservation gaps or integrity checks. After processing ends, explain `archive-summary.html`, resume and separate deletion preview/approval. Completion: each authorized file has a verified output or an explicit kept-original, failed or unfinished outcome; actual savings and potentially reclaimable storage are distinct.
