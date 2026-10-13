# Install ArchiveBench

[Back to the README](../README.md) · [Benchmark guide](benchmark.md) · [Agent workflow](agent-workflow.md)

## Requirements

- Windows is the tested platform. macOS/Linux and their hardware encoders remain experimental.
- Install [uv](https://docs.astral.sh/uv/getting-started/installation/). ArchiveBench needs Python 3.11 or newer; uv can install the requested interpreter.
- Install FFmpeg and ffprobe on PATH. Choose a full build with `libvmaf` and the software encoders you want to test. The [FFmpeg download page](https://ffmpeg.org/download.html) links to platform builds. Windows full builds are available from [Gyan](https://www.gyan.dev/ffmpeg/builds/).
- Allow scratch space for lossless sample references, candidate clips and optional review assets. The source files remain in place.

No runtime Python dependencies or Node installation are needed to run the installed tool. Git is needed only for the source-checkout route below. FFmpeg is installed separately and is not bundled with ArchiveBench.

## Install the command

Install the wheel from the initial GitHub release:

```powershell
uv tool install --python 3.11 https://github.com/Today20092/ArchiveBench/releases/download/v0.1.0/archivebench-0.1.0-py3-none-any.whl
uv tool update-shell
```

Open a new terminal so the executable directory is on PATH, then run:

```powershell
archivebench doctor
archivebench setup --config local-config.json
archivebench benchmark local-config.json --output runs/first-test
```

Review the saved configuration before benchmarking, including the proposed fresh validation sections. Open `runs/first-test/report.html` when the command finishes. Keep its companion folder beside it for optional review media.

Without installing a persistent command, use `uv tool run --from` with the same wheel URL and `archivebench` followed by a subcommand. This project is distributed through GitHub Releases; these commands do not assume a PyPI release.

## Install a source checkout

This is the recommended route for agents and people modifying the tool. It includes the local instructions, documentation and tests:

```powershell
git clone https://github.com/Today20092/ArchiveBench.git
cd ArchiveBench
uv sync --locked --python 3.11
uv run archivebench doctor
uv run archivebench setup --config local-config.json
uv run archivebench benchmark local-config.json --output runs/first-test
```

Follow [AGENTS.md](../AGENTS.md) and the [agent workflow](agent-workflow.md) when adapting or operating the checkout. Developers rebuilding the report also need Node; see [development checks](development.md).

## Check the environment

`doctor` lists the FFmpeg version, `libvmaf` presence and configured encoders. A listed GPU encoder still needs a successful compatibility probe during the benchmark. Drivers, devices and the selected pixel format can make an encoder unusable.

If `doctor` cannot find FFmpeg/ffprobe, fix PATH and open a new terminal. If `libvmaf` is absent, select a build containing it before running quality tests. An unavailable GPU encoder is a reported failed probe; it does not justify silently changing Match source to a lower-chroma format.

For the benchmark, saved `ffmpeg` and `ffprobe` fields can select explicit executable paths. They remain local configuration data. Agent-operated archive and cleanup jobs also need the chosen tools available on PATH.
