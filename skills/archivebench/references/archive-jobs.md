# Run a reusable archive

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
