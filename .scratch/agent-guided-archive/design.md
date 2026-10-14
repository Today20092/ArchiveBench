# Decisions and implementation map

## Interview record

The user accepted: completed-project users; replacement of originals as the eventual storage-saving goal; trustworthy comparisons on their footage; small experiments that expand based on evidence; reusable presets with measured quality/size/time and Pareto comparisons; quality acceptance through visual examples; short checks before reusing presets on different footage; preserved video properties/audio with explicit conversions; project reopening as acceptance; keep-original outcomes; explicit per-file exceptions; resumable archive execution; and separate verified cleanup.

'Overnight' was clarified as encoding patience, not a deadline. The final packaging decision is an installable skill plus a standalone terminal workflow sharing the same implementation. The archive runner must work across folders and projects. The user explicitly confirmed moving to planning on 2026-10-14. No product questions remain blocking this plan.

## Existing implementation inspected

| Capability | Existing location | Work needed |
|---|---|---|
| CLI setup, doctor, scan, benchmark/report, archive/cleanup | `archivebench/cli.py` | Keep one public CLI; add missing preset/job/review operations and non-agent guidance. |
| Multi-target search, cached trials, repeat control and budget | `archivebench/core.py`, `archivebench/validation.py` | Bounded initial experiment planning, useful stage counts, pilot-based estimates and explicit expansion. Current upper bounds can be very large. |
| Encoder/rate controls and video policy | `archivebench/encoders.py`, `archivebench/formats.py` | Reuse exact supported controls; expose them in preset explanations and scope checks. |
| Quality/size/time charts and archive-settings export | `report/math.js`, `report/app.js`, `archivebench/report.py` | Add durable visual decisions and scoped preset export without inventing validation. |
| Browser playback and still review | `archivebench/media.py`, `archivebench/stills.py`, `report/playback.js`, `report/stills.js` | Retain fallback; integrate a native viewer for exact candidate files. Browser conversions are not full-fidelity evidence. |
| Reusable folder archive and manifest | `archivebench/archive.py:archive` | Already accepts roots/settings, preserves relative folders, resumes and verifies. Extend with job configuration, explicit exceptions and acceptance evidence. |
| Separate cleanup | `archivebench/archive.py:cleanup` | Preserve current whole-selection validation; add job-specific visual/editor acceptance requirements for the new workflow. |
| Agent operating instructions | `docs/agent-workflow.md` | Reuse as detailed reference behind a distributable skill. No existing SKILL.md package found in the repository file inventory. |

Code discovery used the graph for CLI/archive symbols and the archive call chain. Existing tracked modifications belong to the earlier quality-level/repeat work and remain untouched by this planning change.

## Decisions for implementation

### Portable preset schema (ticket 02)

Use an `archive-preset` version 1 wrapper around the existing version 2 `archive-settings`: name, description, exact canonical encoder options, footage/environment scope, and evidence with a fingerprint of the settings. Presets contain no source/destination paths or checkpoint state. Legacy settings import with unknown scope and unreviewed evidence. Inspection distinguishes hardware/format incompatibility from untested footage; skipping a check never creates current-project validation. Changing settings invalidates the saved evidence fingerprint. CLI import/inspect/export and a separate report preset export share this contract; legacy report exports remain available.

Public APIs in `archivebench.presets`: `make_preset(settings, name='', description='')`, `resolve_settings(document)` (validates wrapper or legacy settings and returns the archive-settings dict), `inspect_preset(document, context=None)`, and `settings_fingerprint(settings)` (canonical JSON content binding, not an authenticity signature). Inspection context may provide `supported_encoders`, `supported_pixel_formats`, `footage` characteristics and `skip_sample_check`; it always reports `current_project_validated: false`. CLI: `preset import|export INPUT --output NEW_PATH [--name NAME --description TEXT]`; `preset inspect INPUT [--context OBSERVATIONS.json]`. Import/export preserve an existing preset's evidence. `archive --settings PRESET.json` resolves the same settings. Encoding remains derived from supported adapters, never arbitrary preset option execution.

- Extend the existing CLI and archive runner rather than generating a different encoder program for each user. A convenience script may accept preset, source and destination arguments and forward them to the installed command.
- Keep reusable preset data separate from per-project paths and checkpoints. Snapshot resolved settings into each job so editing a preset cannot silently change a resumed job.
- Keep the skill small and reference branch-specific instructions. First skill version uses working commands; later tickets extend both interfaces together. Do not document proposed CLI syntax as available functionality.
- Reuse native comparison software. `video-compare` is the first integration candidate; Open RV is a possible later alternative, not a required second integration.
- Record visual decisions against concrete candidates/intervals and source identity. Record editor acceptance against actual job outputs. Treat both as user attestations, not automated proofs.
- Preserve old evidence and compatibility. Plan schema versioning and migration explicitly in the preset/job tickets; no casual reinterpretation of old validation flags.

## Research references

### Agent Skills standard

The user supplied the Agent Skills overview as packaging guidance. On 2026-10-14, fetched the [documentation index](https://agentskills.io/llms.txt), then the linked specification, script guidance and evaluation guidance. Context7 lookup returned unrelated skill collections rather than the official standard, so the primary documentation was used directly.

- [Specification](https://agentskills.io/specification): use a directory named for the skill with YAML-frontmatter `SKILL.md`, required `name` and `description`, and optional resources. Keep the main instructions short and use skill-relative references loaded when needed. Validate the package with the reference validator. Client tool permissions and installation locations are not portable guarantees.
- [Scripts guidance](https://agentskills.io/skill-creation/using-scripts): a skill can invoke an existing installed package; a bundled scripts directory is optional. Our skill should call the same ArchiveBench CLI available to terminal users rather than copy the engine into the skill.
- [Evaluation guidance](https://agentskills.io/skill-creation/evaluating-skills): test realistic task outcomes and compare behavior with and without the skill. This directly tests the product's claimed advantage over a capable agent using the tools unaided.

Packaging target: `skills/archivebench/SKILL.md` with focused `references/` and optional `assets/` or thin `scripts/`. These are planned paths, not an already delivered package. Test installation/discovery on named clients before claiming client compatibility. No vendor-specific plugin server is required by the design.

### Visual comparison

- [video-compare](https://github.com/pixop/video-compare): synchronized video wipe, frame step, zoom and difference views, Windows builds, CLI integration. Optional 10-bit display depends on the display/driver; no audio playback. External program integration first; review license/distribution terms before bundling.
- [Open RV](https://github.com/AcademySoftwareFoundation/OpenRV): more extensive review/color environment, more setup. Defer integration unless the simpler viewer cannot meet verified needs.

Neither viewer has been installed or validated on the camera footage. The native-viewer ticket owns that verification. Existing browser review remains available when the optional viewer is absent.

## Known replacement limits

The runner currently writes `.archive.mkv`, rejects data/unknown streams and attached pictures, and cannot certify proprietary metadata or editor relinking. Camera timecode/data, sidecars, filenames and container support need explicit handling or a keep-original outcome. Do not advertise general camera-original replacement until the acceptance path has been demonstrated.

## Delivery sequence

1. Package the skill around current supported commands and establish the preset contract.
2. Add bounded experiments and native review, plus reusable jobs with explicit exceptions.
3. Complete editor/cleanup acceptance and test the same end-to-end workflow through both entry points.

Implementation details such as exact new subcommand names, JSON field names and editor-specific instructions are engineering choices within this spec. Validate them against current dependencies and editor behavior during the relevant ticket. They do not require another product interview.

The active camera benchmark is independent of this plan. Do not change runner fingerprints or restart it merely to implement this plan; coordinate implementation in an isolated checkout or after the running experiment is safely finished, preserving its exact runner and configuration.
