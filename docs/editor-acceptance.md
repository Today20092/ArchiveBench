# Accept archive replacements and optionally review them

Archive verification checks hashes, video properties, frame count, boundaries, retained streams and copied payloads. A successful encode does not establish visual acceptance or editor compatibility. New folder jobs require an explicit decision tied to the current job mapping, settings and exact verified source/output hashes. Choose either actual visual and editor attestations or quality-tradeoff acceptance without inspection. Visual spot-checking, grading and editor reopening are optional. Benchmark review and preset evidence cannot supply job consent.

## Tested synthetic path

On Windows, DaVinci Resolve Studio **21.1.1.10** imported an H.265 Main10 MOV source and reopened a separate project copy after replacing it with the runner's **H.265 Main10 MKV** output. The synthetic source was 640×360, 30 fps, 90 frames, 10-bit 4:2:0 with **four separate mono PCM 24-bit/48 kHz tracks**. ArchiveBench verified copied audio payloads and full video decode. Resolve reported four audio channels/tracks, 10-bit video, Online status and the original 0–90 timeline boundaries after saving, closing and reopening the copy. Every video/audio timeline item referenced the candidate path.

Actual native UI observation displayed the beginning and a moving frame at 00:00:02:05 during playback with active audio meters. End-frame seeking succeeded. Audio was not listened to by a person; meters and copied-payload verification do not constitute subjective listening acceptance. The initial disposable project's inherited 4096×2160 timeline showed the small 640×360 image centered; the disposable copy's timeline was explicitly set to 640×360 for inspection. No personal project settings were changed. This demonstration does not certify camera metadata, timecode, HDR/log grading, subclips, effects, proxies, other codecs, other editor versions or other NLEs.

## Accept without inspection

After processing ends, use the guided **Accept / cleanup** tab: enter your name and decision note, choose **Accept quality tradeoff without inspection**, then separately preview deletion. The preview lists exact eligible original paths. Only **Approve permanent deletion of previewed originals** deletes them; accepting or encoding never does. Existing completed jobs can be loaded with `archivebench-tui --job SAVED.job.json` (or the desktop launcher).

The same explicit decision is available from the CLI:

```powershell
archivebench acceptance record --output ARCHIVE_FOLDER --kind quality-tradeoff --decision accept --reviewer "User" --note "Accept this preset's quality loss without visual or editor inspection"
archivebench cleanup --output ARCHIVE_FOLDER
# Only after approving the exact preview:
archivebench cleanup --output ARCHIVE_FOLDER --execute --reviewed
```

`--reviewed` approves the deletion preview; for new jobs it does not assert visual/editor inspection. Quality-tradeoff acceptance is stored separately from actual reviews and does not invent them. Declared unmet requirements, preservation gaps, insufficient savings, failed verification or changed/missing files still keep originals. A changed job or mapping needs fresh consent and preview. A later genuine visual/editor rejection blocks earlier quality-tradeoff consent; accepting that observed loss requires a new explicit quality-tradeoff decision. Unmet preservation requirements remain blocking until resolved in the original review record.

## Optional visual and editor workflow

1. Run `archivebench acceptance inspect --output ARCHIVE_FOLDER`. Its deterministic mapping names each original, replacement, exact settings and retained-stream policy. Use this mapping rather than guessing names or extensions.
2. Export/save a **separate project copy** before changing media references. Keep the original project and source files. In Resolve, match each media pool item's File Path to the mapping and use `ReplaceClipPreserveSubClip(candidate_path)` for a changed filename/container. Folder-only relinking is insufficient when `clip.mov` becomes `clip.mov.archive.mkv`. Check every return value and reference. Never edit the only project automatically.
3. Save, close and reopen the copy. Confirm every intended media reference points to its replacement and is online. Inspect beginning/middle/end, edits and duration, color/grades, required metadata, all audio tracks and synchronization. Listen to audio. Check any subclips, multicam, effects or proxies used by that project. If any required property fails, retain the relevant original using a job exception.
4. Record actual human decisions separately:

```powershell
archivebench acceptance record --output ARCHIVE_FOLDER --kind visual --decision accept --reviewer "Reviewer" --note "Reviewed picture, color and all audio; acceptable for intended revisions"
archivebench acceptance record --output ARCHIVE_FOLDER --kind editor --decision accept --reviewer "Reviewer" --editor "DaVinci Resolve Studio VERSION" --project-copy "Reviewed project copy identifier" --note "Saved, closed, reopened; checked mapped references, edits and all audio"
```

Use `--decision reject` and repeat `--unmet-requirement "description"` for required information that was not retained. Acceptance with unmet requirements is refused. An agent may record a human's stated decision, but must never invent it from metrics, process launch or successful API calls.

5. Preview separately with `archivebench cleanup --output ARCHIVE_FOLDER`. Only current accepted replacements appear. If the human explicitly authorizes deletion after the preview, use `--execute --reviewed`. The runner revalidates the entire selection under the job lock before deleting any original, including each file's saved exception settings. Changed files, mappings, settings or missing acceptance refuse cleanup.

## Keep-original boundaries and legacy manifests

Data/unknown streams, multiple video streams and cover art remain unsupported job inputs. Timecode follows the explicit job policy: reject blocks timecoded input, preserve uses the supported MOV/MP4 preservation and verification path, and drop explicitly removes timecode. Matching `.xmp`, `.xml`, `.bim`, `.cpi` or `.thm` sidecars remain a keep-original boundary; no tested sidecar preservation path is implemented. Other proprietary camera structures and sidecars cannot be detected comprehensively: declare requirements and retain originals when preservation is untested. Compression cannot preserve RAW sensor controls merely by copying metadata.

New job acceptance is stored in `archive-manifest.json`, independently from preset/benchmark review. Changed identities invalidate it. Legacy manifests without a `job` retain their existing separate `--execute --reviewed` cleanup contract; they are not silently migrated or retrospectively labeled editor-approved. To use the stronger gate, create a new job and explicitly accept its verified outputs.
