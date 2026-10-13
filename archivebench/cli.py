"""The same CLI is used by people, Codex and Claude."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .archive import archive, candidates, cleanup
from .core import benchmark, primary, probe, run, save, validate_config
from .encoders import SPECS, discover
from .report import write_report
from .formats import VARIANT_PRESETS, output_video


def wizard(config_path: Path) -> None:
    root = Path(input("Source clip or folder: ").strip().strip('"')).resolve()
    files = candidates(root) if root.is_dir() else [root]
    if not files:
        raise ValueError("No eligible clips found")
    for i, path in enumerate(files):
        print(f"{i + 1}: {path.name}")
    selection = input("Choose clip numbers (comma-separated, e.g. 1,3,5): ")
    picked = [files[int(number.strip()) - 1] for number in selection.split(",")]
    profile = input("Profile compact/editing [compact]: ").strip() or "compact"
    mode = input("Mode quick/thorough [quick]: ").strip() or "quick"
    for index, variant in enumerate(VARIANT_PRESETS, 1):
        print(f"{index}: {variant['label']} ({variant['pixel_format']}, {variant['resolution']})")
    choice = (
        input(
            "Choose format preset numbers, comma-separated [1]; or source/yuv420p/yuv420p10le/yuv422p/yuv422p10le for a custom variant: "
        ).strip()
        or "1"
    )
    if choice in ("source", "yuv420p", "yuv420p10le", "yuv422p", "yuv422p10le"):
        pixel = choice
        resolution = (
            input("Resolution original/2160p/1440p/1080p/720p [original, never upscale]: ").strip()
            or "original"
        )
        variants = [
            {"id": "custom", "label": "Custom", "pixel_format": pixel, "resolution": resolution}
        ]
    else:
        numbers = [int(number.strip()) for number in choice.split(",")]
        if any(number < 1 or number > len(VARIANT_PRESETS) for number in numbers):
            raise ValueError("Choose a listed format preset number")
        variants = [dict(VARIANT_PRESETS[number - 1]) for number in numbers]
        pixel, resolution = variants[0]["pixel_format"], variants[0]["resolution"]
    print(
        "Each named combination is tested separately. Edit its label and video policy in the saved config. Expanding bit depth/chroma cannot restore absent detail."
    )
    print(
        "The benchmark measures video only. These retention choices are saved for archive export."
    )
    audio_mode = input("Audio copy/aac/none [copy, keep original audio]: ").strip() or "copy"
    drop = input("Audio track numbers to omit, comma-separated [none; keep every track]: ").strip()
    drop_tracks = [int(number.strip()) for number in drop.split(",")] if drop else []
    audio_rate = int(input("AAC kbps per channel [192]: ") or "192") if audio_mode == "aac" else 192
    subtitles = input("Subtitles copy/drop [copy]: ").strip() or "copy"
    attachments = input("Attachments copy/drop [copy]: ").strip() or "copy"
    metadata = input("Metadata and chapters copy/drop [copy]: ").strip() or "copy"
    budget = float(input("Time budget in minutes [15]: ") or "15")
    samples = []
    for path in picked:
        duration = float(probe(path)["format"]["duration"])
        start = float(input(f"{path.name}: sample start in seconds [0]: ") or "0")
        seconds = min(6 if mode == "quick" else 20, max(0, duration - start))
        print(
            f"Sample: {start:.1f}s to {start + seconds:.1f}s; choose different scenes for motion, detail and noise."
        )
        samples.append({"path": str(path), "label": path.name, "start": start, "seconds": seconds})
    config = {
        "version": 1,
        "profile": profile,
        "mode": mode,
        "pixel_format": pixel,
        "resolution": resolution,
        "variants": variants,
        "audio_mode": audio_mode,
        "drop_audio_tracks": drop_tracks,
        "audio_kbps_per_channel": audio_rate,
        "subtitles": subtitles,
        "attachments": attachments,
        "metadata": metadata,
        "target_vmaf": 93 if profile == "compact" else 96,
        "tolerance": 0.5,
        "budget_minutes": budget,
        "samples": samples,
        "encoders": [],
    }
    if config_path.exists():
        raise ValueError("Config already exists; choose a new path")
    validate_config(config)
    for variant in variants:
        for path in picked:
            video = primary(probe(path))
            try:
                target = output_video(video, variant)
                print(
                    f"{variant['label']} / {path.name}: {video['width']}x{video['height']} {video['pix_fmt']} -> {target['width']}x{target['height']} {target['pix_fmt']}"
                )
            except ValueError as error:
                print(f"{variant['label']} / {path.name}: unsupported: {error}")
    passes, finalists = (2, 4) if mode == "quick" else (4, 8)
    print(
        f"Estimated upper bound before compatibility checks: {len(variants) * len(samples) * len(SPECS)} encoder screens; {len(variants) * len(samples) ** 2 * finalists * passes} tuning trials including shared settings on every sample. Only installed compatible encoders run, and adaptive tuning may stop earlier."
    )
    save(config_path, config)
    print(
        f"Saved {config_path}. Review it, then run: archivebench benchmark {config_path} --output runs/my-test"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local archival encoding benchmarks and offline reports"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    setup = commands.add_parser(
        "setup", help="Guided clip selection and saved experiment configuration"
    )
    setup.add_argument("--config", type=Path, default=Path("local-config.json"))
    commands.add_parser("doctor", help="List installed encoders and quality scoring support")
    scan = commands.add_parser(
        "scan", help="List eligible clips; proxies/generated archives excluded"
    )
    scan.add_argument("source", type=Path)
    bench = commands.add_parser("benchmark", help="Run or resume a saved experiment")
    bench.add_argument("config", type=Path)
    bench.add_argument("--output", type=Path, required=True)
    report = commands.add_parser(
        "report", help="Regenerate HTML/CSV/Markdown from existing results"
    )
    report.add_argument("results", type=Path)
    batch = commands.add_parser("archive", help="Review or execute optional archive starter runner")
    batch.add_argument("--source", type=Path, required=True)
    batch.add_argument("--output", type=Path, required=True)
    batch.add_argument("--settings", type=Path, required=True)
    batch.add_argument("--execute", action="store_true")
    clean = commands.add_parser(
        "cleanup", help="Separate verified-original cleanup; dry-run by default"
    )
    clean.add_argument("--output", type=Path, required=True)
    clean.add_argument("--execute", action="store_true")
    clean.add_argument("--reviewed", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "setup":
            wizard(args.config)
        elif args.command == "doctor":
            supported, other = discover(run(["ffmpeg", "-encoders"]))
            print(
                json.dumps(
                    {
                        "ffmpeg": run(["ffmpeg", "-version"]).splitlines()[0],
                        "libvmaf": "libvmaf" in run(["ffmpeg", "-filters"]),
                        "configured": supported,
                        "unconfigured": other,
                        "note": "Encoder listing is followed by an actual compatibility probe during benchmark",
                    },
                    indent=2,
                )
            )
        elif args.command == "scan":
            print(json.dumps([str(path) for path in candidates(args.source.resolve())], indent=2))
        elif args.command == "benchmark":
            result = benchmark(args.config, args.output)
            print(write_report(result, args.output))
        elif args.command == "report":
            print(
                write_report(
                    json.loads(args.results.read_text(encoding="utf-8")), args.results.parent
                )
            )
        elif args.command == "archive":
            archive(args.source, args.output, args.settings, args.execute)
        elif args.command == "cleanup":
            cleanup(args.output, args.execute, args.reviewed)
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print(f"ArchiveBench: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    except KeyboardInterrupt:
        print(
            "Stopped. Saved trials remain available; rerun the same configuration to resume.",
            file=sys.stderr,
        )
        raise SystemExit(130) from None


if __name__ == "__main__":
    main()
