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

### Optional native visual review

Install [video-compare](https://github.com/pixop/video-compare) independently and put its executable on PATH. ArchiveBench does not bundle this GPL-2.0 program. Missing viewer support leaves the existing browser report, stills and converted playback available.

```powershell
archivebench review inspect --results runs/first-test/results.json --trial TRIAL_ID
archivebench review launch --results runs/first-test/results.json --trial TRIAL_ID
archivebench review record --results runs/first-test/results.json --trial TRIAL_ID --decision reject --reviewer "Editor" --method native --objections "0.5,1.2" --note "Artifacts around hair"
archivebench review inspect --results runs/first-test/results.json
```

Choose the exact trial ID from `results.json`. Launch checks hashes and decoded frame timestamps/counts, frame rate and dimensions of the source interval reference and measured encode. Both paths must remain inside the benchmark folder. It uses argument arrays rather than shell commands. Saved `visual-reviews.json` decisions remain separate from metrics and appear in regenerated reports; changed media or interval identities invalidate them. Objection timestamps are relative to the reviewed sample, not the full source. Recording is your attestation that you reviewed the footage; launching does not record acceptance.

The viewer receives exact files with automatic options/filter insertion and tone mapping disabled. YUV/RGB conversion and display scaling still occur. Inspect color tags and use an independently verified viewing transform for Log/HDR material; no grading-fidelity guarantee is provided. Default display is 8-bit. `--display-bits 10` requests the viewer's 10-bit path, but does not certify monitor/driver fidelity. The viewer is silent: retained audio needs a separate listening check. Browser previews convert to 8-bit 4:2:0 and cannot establish original 10-bit or chroma fidelity.

The tested Windows synthetic smoke used a 3-second 24 fps, 640×360 10-bit 4:2:0 FFV1 reference and HEVC candidate with moving markers/frame numbers. Both decoded 72 aligned frames. An actual native window showed matching positions and timestamps; requested 10-bit rendering reported an ARGB2101010 video surface. This is display-path smoke evidence, not camera-footage quality acceptance or a physical 10-bit/HDR monitor certification.

`doctor` lists the FFmpeg version, `libvmaf` presence and configured encoders. A listed GPU encoder still needs a successful compatibility probe during the benchmark. Drivers, devices and the selected pixel format can make an encoder unusable.

If `doctor` cannot find FFmpeg/ffprobe, fix PATH and open a new terminal. If `libvmaf` is absent, select a build containing it before running quality tests. An unavailable GPU encoder is a reported failed probe; it does not justify silently changing Match source to a lower-chroma format.

For the benchmark, saved `ffmpeg` and `ffprobe` fields can select explicit executable paths. They remain local configuration data. Agent-operated archive and cleanup jobs also need the chosen tools available on PATH.

## Install the optional agent skill

Wheels built from this revision include the portable `archivebench` skill and all its references. Earlier published wheels may predate the installer; use the source-checkout route until a release containing it is available. The skill invokes the same command used in the terminal; it has no separate encoding engine or API-key requirement. Install it into your client's chosen skill directory:

```powershell
archivebench-skill --destination PATH_TO_CLIENT_SKILLS
```

For a source checkout, use `uv run archivebench-skill --destination PATH_TO_CLIENT_SKILLS`. The installer creates an `archivebench` subfolder and refuses to overwrite an existing skill. Review an existing installation before replacing it. Keep the installed skill and tool from the same release.

Choose the discovery directory using your client's documentation; clients use their own locations and may require a reload or enable step. No client configuration is modified by this installer. See the [Agent Skills client list](https://agentskills.io/clients) for links to client instructions. Format compatibility does not establish execution support: the agent needs local filesystem and terminal access plus the installed ArchiveBench and FFmpeg tools. A web-only agent without these capabilities cannot process local footage through the skill.

Verify discovery in your client by invoking `$archivebench` with a completed-project archival request. Ask it to locate the command, inspect its help and run `archivebench doctor` before proposing an encode. The skill should also activate for archive-codec comparisons or preset reuse, and should not activate for ZIP archives, image compression or ordinary delivery exports. These are suggested behavioral smoke cases, not a claim that every client has been tested.

The [packaged skill](../skills/archivebench/SKILL.md) contains the shared decision workflow. Client-specific installation details live here. Terminal users can continue directly with the command and do not need the skill.
