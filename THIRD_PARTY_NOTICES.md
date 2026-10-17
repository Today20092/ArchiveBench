# Third-party notices

Native driver query bindings reference NVIDIA NVENC and AMD AMF interface declarations. Their MIT notices ship in [native-notices.txt](archivebench/native-notices.txt). No vendor SDK or driver binaries are bundled.

The terminal UI uses Textual (MIT), with Python dependencies resolved in `uv.lock`. Textual's license is provided in its installed distribution: https://github.com/Textualize/textual/blob/main/LICENSE. Dependency license files must accompany redistributed packages.

The offline report bundles `@tanstack/charts` 1.1.0 and its JavaScript dependencies. Their retained license comments are included in `archivebench/assets/report.js`. Dependency versions and integrity hashes are recorded in `package-lock.json`; inspect each package's license when redistributing modified bundles.

TanStack Charts: Copyright TanStack contributors, MIT license. See https://github.com/TanStack/charts/blob/main/LICENSE.

The report uses system fonts and includes no downloaded font assets. FFmpeg, its codec implementations and VMAF are installed separately; their licenses and codec patent obligations are independent of this project's source license. This repository does not bundle FFmpeg or camera footage.

Optional native review invokes an independently installed [video-compare](https://github.com/pixop/video-compare), licensed GPL-2.0. No executable or source from it is bundled. Redistributing its binaries requires a separate licensing review and compliance with its license.
