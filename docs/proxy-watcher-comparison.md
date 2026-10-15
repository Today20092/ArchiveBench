# ArchiveBench and Proxy Watcher archiving

Update: the [desktop migration](archive-desktop.md) adds file selection, project defaults, MOV/MP4 policies, progress, failure continuation and selected accepted cleanup. The older comparison below describes the original terminal launcher; it is not the current desktop feature list. Proxy Watcher's old archive engine remains only for legacy manifests and rollback pending real editor acceptance.

ArchiveBench uses the shared `archivebench/windows/archivebench-send-to.ps1` launcher and Python archive-job engine. Install it with `archivebench-send-to --install --preset-directory PRESETS`. Right-click one footage folder, choose **Send to → ArchiveBench**, select a preset, review the preflight and type `ARCHIVE`. Repeating the same selection resumes its saved job. A different preset gets a distinct default output folder. This launcher does not reproduce Proxy Watcher's graphical checkbox picker or its Nilesoft menu.

| Behavior | Proxy Watcher archive script | ArchiveBench launcher |
|---|---|---|
| Interface | Nilesoft Media Tools, graphical file selection, WezTerm progress | Windows Send to, numbered preset selection, terminal preflight |
| Settings | Built-in presets and editable controls | Portable JSON presets with exact controls and measured historical evidence |
| Default destination | Project `Archived Footage` | `<source>-Archived-<preset-filename>`; custom output supported |
| Container | HEVC MOV; AV1 MP4 | MKV |
| Audio defaults | Drop tracks 3–4; convert remaining audio to AAC | These measured presets copy all tracks |
| Camera data | Omits camera-specific data/cover art, carries supported timecode | Unsupported data/timecode preservation blocks encoding or keeps originals |
| Resume | Hash-verified manifest; interrupted files restart | Hash-verified job snapshot and manifest; interrupted files restart |
| Removal | Separate selected-file cleanup | Separate cleanup with recorded visual/editor acceptance for jobs |

The measured candidates are CPU HEVC medium/CRF 24 with source chroma, NVIDIA HEVC P5/HQ/VBR/CQ 28 with 10-bit 4:2:0, and CPU SVT-AV1 preset 6/CRF 32 with 10-bit 4:2:0. The last two reduce chroma for 4:2:2 sources. Preserve-color uses source format rather than forcing every future source to 4:2:2. All retain original dimensions and frame rate. They remain measured starting points until actual visual/editor review; saving a preset does not imply acceptance.

Use the actual footage folder with ArchiveBench rather than assuming it will select only an `Original Footage` subtree from a whole project. Preflight must show the intended files. MOV/MP4 versus MKV, renamed outputs, and audio layout can affect editor relinking. Do not carry over Proxy Watcher's audio/data omission policy implicitly.

See [archive jobs](archiving.md) and [Send to details](windows-send-to.md). Full-source archives have not been created merely by installing this launcher.
