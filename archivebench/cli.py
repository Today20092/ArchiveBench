"""The same CLI is used by people, Codex and Claude."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .archive import archive, candidates, cleanup
from .core import benchmark, primary, probe, run, save, validate_config
from .encoders import discover
from .report import write_report
from .formats import VARIANT_PRESETS, output_video
from .validation import quality_targets, validation_sections
from .presets import inspect_preset, make_preset, resolve_settings, starter_paths
from .experiments import experiment_plan
from .jobs import create_job, run_job
from .review import inspect_review, launch_review, prepare_review, record_review, saved_reviews
from .acceptance import inspect_acceptance, record_acceptance


def wizard(config_path: Path, comparison: str = "initial", strategy: str = "tune") -> None:
    root = Path(input("Source clip or folder: ").strip().strip('"')).resolve()
    files = candidates(root) if root.is_dir() else [root]
    if not files:
        raise ValueError("No eligible clips found")
    for i, path in enumerate(files):
        print(f"{i + 1}: {path.name}")
    selection = input("Choose clip numbers (comma-separated, e.g. 1,3,5): ")
    picked = [files[int(number.strip()) - 1] for number in selection.split(",")]
    if strategy == "tune" and comparison == "initial" and len(picked) > 2:
        raise ValueError(
            "Initial comparison accepts at most two clips; use setup --comparison comprehensive for wider coverage"
        )
    profile = input("Profile compact/editing [compact]: ").strip() or "compact"
    mode = (
        (input("Mode quick/thorough [quick]: ").strip() or "quick")
        if strategy == "tune"
        else "quick"
    )
    encoders = [
        value.strip()
        for value in (
            input("Encoders, comma-separated [libx265,libsvtav1,hevc_nvenc; or all]: ").strip()
            or "libx265,libsvtav1,hevc_nvenc"
        ).split(",")
    ]
    if encoders == ["all"]:
        if strategy == "fixed":
            encoders, _ = discover(run(["ffmpeg", "-encoders"]))
        elif comparison != "comprehensive":
            raise ValueError("All encoders requires setup --comparison comprehensive")
        else:
            encoders = []
    encode_repeats = int(
        input(
            "Measured encodes per setting [1; use 2, 3 or more only to repeat timing measurements]: "
        ).strip()
        or "1"
    )
    targets = (
        quality_targets(
            {
                "target_vmafs": [
                    float(value.strip())
                    for value in (
                        input(
                            "VMAF targets, comma-separated [80,90,95,97; or one target]: "
                        ).strip()
                        or "80,90,95,97"
                    ).split(",")
                ]
            }
        )
        if strategy == "tune"
        else [95]
    )
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
    budget = float(input("Total time budget in minutes [30]: ") or "30")
    samples = []
    for path in picked:
        duration = float(probe(path)["format"]["duration"])
        start = float(input(f"{path.name}: sample start in seconds [0]: ") or "0")
        seconds = min(
            5 if strategy == "fixed" else 6 if mode == "quick" else 20, max(0, duration - start)
        )
        print(
            f"Sample: {start:.1f}s to {start + seconds:.1f}s; choose different scenes for motion, detail and noise."
        )
        samples.append({"path": str(path), "label": path.name, "start": start, "seconds": seconds})
    config = {
        "version": 1,
        "profile": profile,
        "mode": mode,
        "comparison": comparison,
        "encode_repeats": encode_repeats,
        "pixel_format": pixel,
        "resolution": resolution,
        "variants": variants,
        "audio_mode": audio_mode,
        "drop_audio_tracks": drop_tracks,
        "audio_kbps_per_channel": audio_rate,
        "subtitles": subtitles,
        "attachments": attachments,
        "metadata": metadata,
        "target_vmaf": max(targets),
        "target_vmafs": targets,
        "tolerance": 0.5,
        "budget_minutes": budget,
        "samples": samples,
        "encoders": encoders,
    }
    if strategy == "fixed":
        from .experiments import fixed_settings

        config["strategy"] = "fixed"
        config["fixed_settings"] = fixed_settings(config)
        config.pop("target_vmafs")
        config.pop("target_vmaf")
        validate_config(config)
        if config_path.exists():
            raise ValueError("Config already exists; choose a new path")
        save(config_path, config)
        print(json.dumps(experiment_plan(config), indent=2))
        print(
            f"Saved {config_path}. Fixed settings, no VMAF search. Review the settings and run archivebench benchmark CONFIG --output RUN. Presets are measured starting points; visual review remains separate."
        )
        return
    if config_path.exists():
        raise ValueError("Config already exists; choose a new path")
    validate_config(config)
    durations = {str(path): float(probe(path)["format"]["duration"]) for path in picked}
    proposals = validation_sections(samples, durations)
    unavailable = [section for section in proposals if "unavailable" in section]
    if unavailable:
        config["validation_unavailable"] = [section["unavailable"] for section in unavailable]
        print(
            "Fresh-footage validation unavailable for at least one source. Results remain provisional. Choose shorter tuning sections or longer sources in the saved config."
        )
    else:
        config["validation_samples"] = proposals
        config["validation_reserve"] = 0.3
        for section in proposals:
            print(
                f"Fresh section: {Path(section['path']).name}, {section['start']:.1f}s to {section['start'] + section['seconds']:.1f}s. Review or replace validation_samples in the saved config before running."
            )
        print("One total budget: 70% tuning, 30% reserved for fixed-setting validation.")
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
    print(
        f"Measured encodes per setting: {encode_repeats} for tuning and validation. Repeats improve timing confidence, not picture quality. Screening and pilots are separate."
    )
    print(
        f"Compression tuning searches VMAF {targets} using shared measurements. More targets add distinct settings, not timing repeats. VMAF is a model score, not a percentage of original quality."
    )
    print(
        f"Experiment upper bound and saved choices: {json.dumps(experiment_plan(config))}. Review footage, controls and bounds before execution."
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
    setup.add_argument("--comparison", choices=("initial", "comprehensive"), default="initial")
    setup.add_argument(
        "--strategy",
        choices=("fixed", "tune"),
        default="fixed",
        help="Fixed settings by default; tune opts into VMAF target searches",
    )
    commands.add_parser("doctor", help="List installed encoders and quality scoring support")
    scan = commands.add_parser(
        "scan", help="List eligible clips; proxies/generated archives excluded"
    )
    scan.add_argument("source", type=Path)
    bench = commands.add_parser("benchmark", help="Run or resume a saved experiment")
    bench.add_argument("config", type=Path)
    bench.add_argument("--output", type=Path, required=True)
    plan = commands.add_parser(
        "plan", help="Show saved experiment choices and bounds without encoding"
    )
    plan.add_argument("config", type=Path)
    status = commands.add_parser("status", help="Show progress and completed measurements")
    status.add_argument("output", type=Path)
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
    preset = commands.add_parser(
        "preset", help="Import, inspect or export portable archive presets"
    )
    preset.add_argument("operation", choices=("list", "import", "inspect", "export"))
    preset.add_argument("document", type=Path, nargs="?")
    preset.add_argument("--output", type=Path)
    preset.add_argument("--name", default="")
    preset.add_argument("--description", default="")
    preset.add_argument(
        "--context", type=Path, help="Optional actual compatibility and footage observations"
    )
    job = commands.add_parser("job", help="Create, inspect or run reusable archive folder jobs")
    job.add_argument("operation", choices=("create", "inspect", "run"))
    job.add_argument("config", type=Path)
    job.add_argument("--source", type=Path)
    job.add_argument("--output", type=Path)
    job.add_argument("--preset", type=Path)
    job.add_argument(
        "--exceptions", type=Path, help="JSON list of explicit relative file exceptions"
    )
    job.add_argument("--execute", action="store_true")
    review = commands.add_parser(
        "review", help="Launch exact native comparison or save user visual decisions"
    )
    review.add_argument("operation", choices=("inspect", "launch", "record", "prepare"))
    review.add_argument(
        "--seconds", type=float, default=120, help="Selected review preparation allowance"
    )
    review.add_argument("--results", type=Path, required=True)
    review.add_argument("--trial")
    review.add_argument("--viewer", default="video-compare")
    review.add_argument("--display-bits", type=int, choices=(8, 10), default=8)
    review.add_argument("--decision", choices=("accept", "reject"))
    review.add_argument("--reviewer", default="")
    review.add_argument("--method", choices=("native", "browser", "editor"), default="native")
    review.add_argument("--objections", default="", help="Comma-separated sample-relative seconds")
    review.add_argument("--note", default="")
    acceptance = commands.add_parser(
        "acceptance", help="Inspect job mapping or record actual visual/editor acceptance"
    )
    acceptance.add_argument("operation", choices=("inspect", "record"))
    acceptance.add_argument("--output", type=Path, required=True)
    acceptance.add_argument("--kind", choices=("visual", "editor"))
    acceptance.add_argument("--decision", choices=("accept", "reject"))
    acceptance.add_argument("--reviewer", default="")
    acceptance.add_argument("--editor", default="", help="Editor name and version")
    acceptance.add_argument("--project-copy", default="", help="Reviewed separate project copy")
    acceptance.add_argument("--note", default="")
    acceptance.add_argument("--unmet-requirement", action="append", default=[])
    args = parser.parse_args()
    try:
        if args.command == "acceptance":
            value = (
                inspect_acceptance(args.output)
                if args.operation == "inspect"
                else record_acceptance(
                    args.output,
                    args.kind,
                    args.decision,
                    args.reviewer,
                    editor=args.editor,
                    project_copy=args.project_copy,
                    note=args.note,
                    unmet_requirements=args.unmet_requirement,
                )
            )
            print(json.dumps(value, indent=2))
        elif args.command == "plan":
            config = json.loads(args.config.read_text(encoding="utf-8"))
            validate_config(config)
            print(json.dumps(experiment_plan(config), indent=2))
        elif args.command == "status":
            progress = args.output / "progress.json"
            if progress.exists():
                value = json.loads(progress.read_text(encoding="utf-8"))
            else:
                result = json.loads((args.output / "results.json").read_text(encoding="utf-8"))
                progress = args.output / "results.json"
                value = {
                    "status": result.get("status", "unknown"),
                    "stage": result.get("stage", "unknown"),
                    "completed_trials": len(result.get("trials", [])),
                    "completed_screens": len(result.get("screening", [])),
                    "remaining_work": "unknown; older run has no stage telemetry",
                }
            from datetime import datetime, timezone

            value["checkpoint_status"] = value.pop("status", "unknown")
            value["activity"] = "unknown"
            value["last_updated"] = (
                value.get("updated_at")
                or datetime.fromtimestamp(progress.stat().st_mtime, timezone.utc).isoformat()
            )
            value["activity_note"] = "Saved checkpoint; current process activity is not observed."
            print(json.dumps(value, indent=2))
        elif args.command == "job":
            if args.operation == "create":
                if args.config.exists() or not all((args.source, args.output, args.preset)):
                    raise ValueError(
                        "Choose a new config and supply --source, --output and --preset"
                    )
                exceptions = (
                    json.loads(args.exceptions.read_text(encoding="utf-8"))
                    if args.exceptions
                    else []
                )
                value = create_job(args.source, args.output, args.preset, exceptions)
                save(args.config, value)
                print(args.config)
            else:
                run_job(args.config, args.execute if args.operation == "run" else False)
        elif args.command == "review":
            directory = args.results.resolve().parent
            if args.results.name != "results.json":
                raise ValueError("Choose canonical results.json")
            if args.operation == "inspect":
                value = (
                    inspect_review(directory, args.trial)
                    if args.trial
                    else saved_reviews(directory)
                )
            elif not args.trial:
                raise ValueError("Choose --trial from results.json")
            elif args.operation == "launch":
                value = launch_review(directory, args.trial, args.viewer, args.display_bits)
            elif args.operation == "prepare":
                value = prepare_review(directory, args.trial, args.seconds)
            else:
                value = record_review(
                    directory,
                    args.trial,
                    args.decision,
                    args.reviewer,
                    [float(item.strip()) for item in args.objections.split(",") if item.strip()],
                    args.note,
                    args.method,
                )
                write_report(json.loads(args.results.read_text(encoding="utf-8")), directory)
            print(json.dumps(value, indent=2))
        elif args.command == "preset":
            if args.operation == "list":
                print(
                    json.dumps(
                        [
                            {"path": str(path), **json.loads(path.read_text(encoding="utf-8"))}
                            for path in starter_paths()
                        ],
                        indent=2,
                    )
                )
                return
            if args.document is None:
                raise ValueError(
                    "Supply a preset document path; use preset list for built-in starters"
                )
            document = json.loads(args.document.read_text(encoding="utf-8"))
            settings = resolve_settings(document)
            if args.operation == "inspect":
                context = (
                    json.loads(args.context.read_text(encoding="utf-8")) if args.context else None
                )
                print(json.dumps(inspect_preset(document, context), indent=2))
            else:
                if args.output is None or args.output.exists():
                    raise ValueError("Choose a new --output path")
                value = (
                    document
                    if document.get("type") == "archive-preset"
                    else make_preset(settings, args.name, args.description)
                )
                save(args.output, value)
                print(args.output)
        elif args.command == "setup":
            wizard(args.config, args.comparison, args.strategy)
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
            print(
                json.dumps(
                    {
                        "status": result.get("status"),
                        "comparison_limit_reached": result.get("comparison_limit_reached", False),
                        "completed_trials": len(result.get("trials", [])),
                        "validation_status": result.get("validation_status", "unavailable"),
                        "note": "Completed processing is separate from quality qualification. Review missing/failed evidence before selecting a preset.",
                    }
                )
            )
            print(
                args.output / "report.html"
                if result["config"].get("strategy") == "fixed"
                else write_report(result, args.output)
            )
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
