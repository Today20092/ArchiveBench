"""Experiment runner. A saved specification controls commands, scoring and cache identity."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import statistics
import subprocess
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

from .encoders import SPECS, discover, options
from .formats import format_variants, output_video, scale_filter, validate_formats
from .validation import quality_targets, shortlist, validation_sections
from .experiments import experiment_plan


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def save(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def run(args: list[str], timeout: float = 120) -> str:
    process = subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(0.1, timeout),
    )
    if process.returncode:
        raise RuntimeError(process.stderr[-3000:] or f"Command failed: {args[0]}")
    return process.stdout


def probe(path: Path, ffprobe: str = "ffprobe") -> dict[str, Any]:
    return json.loads(
        run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-show_chapters",
                "-show_data_hash",
                "sha256",
                "-of",
                "json",
                str(path),
            ]
        )
    )


def primary(info: dict[str, Any]) -> dict[str, Any]:
    videos = [
        s
        for s in info["streams"]
        if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")
    ]
    if len(videos) != 1:
        raise ValueError("Exactly one primary video stream is required")
    return videos[0]


def inspect_source(path: Path, start: float, seconds: float, ffprobe: str) -> dict[str, Any]:
    info = probe(path, ffprobe)
    video = primary(info)
    if video.get("color_transfer") in ("smpte2084", "arib-std-b67") or any(
        any(
            word in side.get("side_data_type", "")
            for word in ("DOVI", "Mastering", "Content light")
        )
        for side in video.get("side_data_list", [])
    ):
        raise ValueError("HDR/Dolby Vision is unsupported in this release")
    if video.get("field_order", "unknown") not in ("progressive", "unknown"):
        raise ValueError("Interlaced footage is unsupported")
    fps = Fraction(video["avg_frame_rate"])
    if fps <= 0 or fps != Fraction(video.get("r_frame_rate", "0/1")):
        raise ValueError("Variable/unknown frame rate is unsupported")
    if start < 0 or seconds <= 0 or start + seconds > float(info["format"]["duration"]) + 0.01:
        raise ValueError("Sample interval exceeds the source duration")
    frames = json.loads(
        run(
            [
                ffprobe,
                "-v",
                "error",
                "-read_intervals",
                f"{start}%+{seconds}",
                "-select_streams",
                "v:0",
                "-show_frames",
                "-show_entries",
                "frame=best_effort_timestamp_time",
                "-of",
                "json",
                str(path),
            ]
        )
    )["frames"]
    stamps = [
        float(frame["best_effort_timestamp_time"])
        for frame in frames
        if "best_effort_timestamp_time" in frame
    ]
    # Container timestamps can be coarser than a frame interval (e.g. MKV milliseconds).
    timestamp_tolerance = min(
        float(1 / fps) / 2, max(0.0002, float(Fraction(video.get("time_base", "1/1000000"))))
    )
    if any(abs(b - a - float(1 / fps)) > timestamp_tolerance for a, b in zip(stamps, stamps[1:])):
        raise ValueError("Variable frame timestamps detected")
    if len(stamps) < 2:
        raise ValueError("Insufficient frame timestamps")
    video["fps"] = str(fps)
    video["duration"] = float(info["format"]["duration"])
    video["frames"] = round(seconds * float(fps))
    if video["frames"] < 2:
        raise ValueError("Sample must contain at least two frames")
    return video


def color_args(video: dict[str, Any]) -> list[str]:
    args: list[str] = []
    for key, flag in [
        ("color_range", "-color_range"),
        ("color_space", "-colorspace"),
        ("color_transfer", "-color_trc"),
        ("color_primaries", "-color_primaries"),
    ]:
        if video.get(key) not in (None, "unknown", "unspecified"):
            args.extend([flag, video[key]])
    return args


def encode_args(
    ffmpeg: str,
    source: Path,
    start: float,
    frames: int,
    output: Path,
    encoder: str,
    quality: int,
    pixel_format: str,
    video: dict[str, Any],
    target: dict[str, Any] | None = None,
) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-v",
        "warning",
        "-y",
        "-ss",
        str(start),
        "-i",
        str(source),
        "-map",
        f"0:{video['index']}",
        "-an",
        "-sn",
        "-dn",
        "-frames:v",
        str(frames),
        "-fps_mode",
        "passthrough",
        *options(encoder, quality, pixel_format, scale_filter(video, target or video)),
        "-g",
        str(max(1, round(float(Fraction(video["fps"])) * 8))),
        *color_args(video),
        "-f",
        "matroska",
        str(output),
    ]


def validate_output(
    path: Path, video: dict[str, Any], encoder: str, pixel_format: str, ffprobe: str
) -> None:
    output = primary(probe(path, ffprobe))
    for key in ("width", "height"):
        if output[key] != video[key]:
            raise ValueError(f"Output {key} mismatch")
    if output["pix_fmt"] != pixel_format or output["codec_name"] != SPECS[encoder][0]:
        raise ValueError("Encoder did not preserve requested codec/bit depth/chroma")
    if Fraction(output["avg_frame_rate"]) != Fraction(video["fps"]):
        raise ValueError("Output frame rate mismatch")
    aspect = video.get("display_aspect_ratio")
    if aspect and aspect not in ("0:1", "N/A"):
        actual = output.get("display_aspect_ratio", "0:1")
        if (
            abs(
                float(Fraction(aspect.replace(":", "/")))
                - float(Fraction(actual.replace(":", "/")))
            )
            > 0.001
        ):
            raise ValueError("Output display aspect ratio mismatch")
    for key in ("color_range", "color_space", "color_transfer", "color_primaries"):
        if video.get(key) not in (None, "unknown", "unspecified") and output.get(key) != video[key]:
            raise ValueError(f"Output {key} mismatch")


def score(
    ffmpeg: str,
    encoded: Path,
    reference: Path,
    video: dict[str, Any],
    pixel_format: str,
    directory: Path,
    subsample: int,
    timeout: float,
    ffprobe: str = "ffprobe",
) -> dict[str, Any]:
    fps = Fraction(video["fps"])
    pts = f"settb=AVTB,setpts=N*{fps.denominator}/({fps.numerator}*TB),format={pixel_format}"
    model = "vmaf_4k_v0.6.1" if video["width"] >= 3840 else "vmaf_v0.6.1"
    metric_path = directory / "vmaf.json"
    # Upscale the candidate, not the reference, so scores include downscaling loss.
    upscale = scale_filter(primary(probe(encoded, ffprobe)), video)
    distorted = (upscale + "," if upscale else "") + pts
    metric_filter = (
        f"[0:v]{distorted},split=2[d][ds];[1:v]{pts},split=2[r][rs];"
        f"[d][r]libvmaf=model=version={model}:log_fmt=json:log_path=vmaf.json:"
        f"n_threads=4:n_subsample={subsample}[v];[ds][rs]ssim[s]"
    )
    process = subprocess.run(
        [
            ffmpeg,
            "-v",
            "info",
            "-xerror",
            "-nostdin",
            "-i",
            str(encoded),
            "-i",
            str(reference),
            "-filter_complex",
            metric_filter,
            "-map",
            "[v]",
            "-map",
            "[s]",
            "-f",
            "null",
            os.devnull,
        ],
        cwd=directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(0.1, timeout),
    )
    (directory / "scoring.log").write_text(process.stderr, encoding="utf-8")
    if process.returncode:
        raise RuntimeError("Quality scoring failed: " + process.stderr[-2000:])
    import re

    ssim = re.search(r"SSIM .*All:([\d.]+)", process.stderr)
    data = json.loads(metric_path.read_text(encoding="utf-8"))
    if len(data["frames"]) != math.ceil(video["frames"] / subsample) or not ssim:
        raise ValueError("Scoring frame count mismatch")
    # SSIM frame coverage also verifies full decode frame alignment, independent of VMAF subsampling.
    counted = int(
        run(
            [
                ffprobe,
                "-v",
                "error",
                "-count_frames",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=nb_read_frames",
                "-of",
                "default=nw=1:nk=1",
                str(encoded),
            ]
        ).strip()
    )
    if counted != video["frames"]:
        raise ValueError("Encoded frame count mismatch")
    scores = sorted(frame["metrics"]["vmaf"] for frame in data["frames"])
    return {
        "vmaf": data["pooled_metrics"]["vmaf"]["mean"],
        "vmaf_p5": scores[max(0, int(len(scores) * 0.05) - 1)],
        "ssim": float(ssim.group(1)),
        "vmaf_frames": [
            {
                "frame_index": frame["frameNum"],
                "seconds": float(Fraction(frame["frameNum"], 1) / fps),
                "vmaf": frame["metrics"]["vmaf"],
            }
            for frame in data["frames"]
        ],
    }


def preview(ffmpeg: str, path: Path, output: Path) -> str:
    run(
        [
            ffmpeg,
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(path),
            "-frames:v",
            "1",
            "-vf",
            "scale=640:-2",
            str(output),
        ]
    )
    return "data:image/jpeg;base64," + base64.b64encode(output.read_bytes()).decode()


def validate_config(config: dict[str, Any]) -> None:
    if config.get("version") != 1 or config.get("mode") not in ("quick", "thorough"):
        raise ValueError("Config requires version 1 and mode quick/thorough")
    if config.get("profile") not in ("compact", "editing"):
        raise ValueError("Choose compact or editing profile")
    repeats = config.get("encode_repeats", 1)
    if type(repeats) is not int or repeats < 1:
        raise ValueError("encode_repeats must be a positive integer")
    if not config.get("samples"):
        raise ValueError("Select at least one sample")
    variants = format_variants(config)
    for variant in variants:
        validate_formats({**config, **variant})
    quality_targets(config)
    experiment_plan(config)
    if (
        not math.isfinite(float(config.get("budget_minutes", 0)))
        or float(config.get("budget_minutes", 0)) <= 0
    ):
        raise ValueError("Set a positive time budget")
    for sample in config["samples"]:
        if (
            not Path(sample["path"]).is_file()
            or not 0 <= float(sample["start"])
            or not 0 < float(sample["seconds"]) <= 60
        ):
            raise ValueError("Invalid sample path/interval (maximum 60 seconds)")
    for name in config.get("encoders", []):
        if name not in SPECS:
            raise ValueError(f"Unsupported encoder config: {name}")
    reserve = float(config.get("validation_reserve", 0.3))
    if not math.isfinite(reserve) or not 0 < reserve < 1:
        raise ValueError("Validation reserve must be between zero and one")
    if "validation_samples" in config:
        durations = {
            str(Path(s["path"]).resolve()): float(
                probe(Path(s["path"]), config.get("ffprobe", "ffprobe"))["format"]["duration"]
            )
            for s in config["samples"]
        }
        validation_sections(config["samples"], durations, config["validation_samples"])
    if not 0 <= float(config.get("tolerance", 0.5)) <= 5:
        raise ValueError("VMAF tolerance must be between 0 and 5")
    for name, quality in config.get("quality_overrides", {}).items():
        options(
            name,
            int(quality),
            "yuv420p" if variants[0]["pixel_format"] == "source" else variants[0]["pixel_format"],
        )


def benchmark(config_path: Path, output: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    output = output.resolve()
    sources = config["samples"] + config.get("validation_samples", [])
    if any(Path(sample["path"]).resolve().is_relative_to(output) for sample in sources):
        raise ValueError(
            "Run output folder contains a selected source; choose separate scratch space"
        )
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".lock"
    with lock.open("x", encoding="utf-8") as stream:
        stream.write(str(os.getpid()))
    try:
        try:
            return _benchmark(config, output)
        except subprocess.TimeoutExpired:
            checkpoint = output / "results.json"
            if not checkpoint.exists():
                raise
            result = json.loads(checkpoint.read_text(encoding="utf-8"))
            result["status"] = "budget_exhausted"
            save(checkpoint, result)
            progress_path = output / "progress.json"
            if progress_path.exists():
                progress = json.loads(progress_path.read_text(encoding="utf-8"))
                progress["status"] = "budget_exhausted"
                save(progress_path, progress)
            return result
    except (
        ValueError,
        RuntimeError,
        OSError,
        subprocess.TimeoutExpired,
        KeyboardInterrupt,
    ) as error:
        progress_path = output / "progress.json"
        if progress_path.exists():
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            progress.update(
                status="interrupted" if isinstance(error, KeyboardInterrupt) else "failed",
                error=str(error),
            )
            save(progress_path, progress)
        raise
    finally:
        lock.unlink(missing_ok=True)


def _benchmark(config: dict[str, Any], output: Path) -> dict[str, Any]:
    import platform
    import shutil

    plan = experiment_plan(config)
    result: dict[str, Any] = {}
    progress: dict[str, Any] = {
        "status": "running",
        "stage": "initialization",
        "stages_seen": [],
        "bounds": plan["bounds"],
        "remaining_work": "adaptive; exact count unknown",
        "pilot_estimate": plan["estimate"],
        "measured_encodes_completed": 0,
        "sources_hashed": 0,
    }
    unscored_encodes = 0

    def publish(phase: str, **details: Any) -> None:
        progress.update(details)
        progress["stage"] = phase
        if phase not in progress["stages_seen"]:
            progress["stages_seen"].append(phase)
        progress["completed_trials"] = len(result.get("trials", []))
        progress["completed_screens"] = len(result.get("screening", []))
        successful_screens = {
            (s["sample"], s.get("variant", "legacy"), s["encoder"])
            for s in result.get("screening", [])
        }
        failed_screens = {
            (s.get("sample"), s.get("variant", "legacy"), s.get("encoder"))
            for s in result.get("skipped", [])
            if s.get("reason", "").startswith("Screen failed:")
            or s.get("reason") == "Not present in FFmpeg build"
        }
        progress["failed_screens"] = len(failed_screens - successful_screens)
        progress["screen_checks_remaining"] = max(
            0,
            progress["bounds"]["screens"]
            - progress["completed_screens"]
            - progress["failed_screens"],
        )
        progress["completed_tuning_trials"] = sum(
            t.get("stage", "tuning") == "tuning" for t in result.get("trials", [])
        )
        progress["completed_validation_trials"] = sum(
            t.get("stage") == "validation" for t in result.get("trials", [])
        )
        progress["validation_trials_remaining"] = (
            max(0, progress["frozen_validation_trials"] - progress["completed_validation_trials"])
            if "frozen_validation_trials" in progress
            else None
        )
        progress["reported_skips"] = len(result.get("skipped", []))
        progress["measured_encodes_completed"] = (
            sum(len(t.get("timings", [])) for t in result.get("trials", [])) + unscored_encodes
        )
        progress["tuning_attempts_started"] = result.get("initial_attempts")
        save(output / "progress.json", progress)

    publish("initialization")
    ffmpeg, ffprobe = config.get("ffmpeg", "ffmpeg"), config.get("ffprobe", "ffprobe")
    versions = {}
    for name, executable in [("ffmpeg", ffmpeg), ("ffprobe", ffprobe)]:
        located = shutil.which(str(executable))
        if not located:
            raise ValueError(f"Missing executable: {executable}")
        versions[name] = {"version": run([executable, "-version"]), "sha256": digest(Path(located))}
    if "libvmaf" not in run([ffmpeg, "-filters"]):
        raise ValueError("FFmpeg must include libvmaf")
    available, unknown = discover(run([ffmpeg, "-encoders"]))
    chosen = config.get("encoders") or available
    if not chosen:
        raise ValueError("No configured archival encoders installed")
    plan = experiment_plan({**config, "encoders": chosen})
    progress["bounds"] = plan["bounds"]
    source_hashes = {}
    for sample in config["samples"]:
        source = Path(sample["path"]).resolve()
        if str(source) not in source_hashes:
            publish(
                "hashing",
                current_source=source.name,
                sources_total=len({str(Path(s["path"]).resolve()) for s in config["samples"]}),
            )
            source_hashes[str(source)] = digest(source)
            publish("hashing", sources_hashed=len(source_hashes))
    environment: dict[str, Any] = {
        "platform": platform.platform(),
        "cpu": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "hardware_accelerators": run([ffmpeg, "-hwaccels"]).strip(),
    }
    if shutil.which("nvidia-smi"):
        try:
            environment["nvidia_gpu_driver_memory"] = run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,driver_version,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                10,
            ).strip()
        except (RuntimeError, subprocess.TimeoutExpired):
            environment["nvidia_gpu_driver_memory"] = "Unavailable"
    identity = fingerprint(
        {
            "protocol": 1,
            "config": config,
            "sources": source_hashes,
            "tools": versions,
            "adapters": SPECS,
            "runner_sha256": digest(Path(__file__)),
            "adapters_sha256": digest(Path(__file__).with_name("encoders.py")),
            "formats_sha256": digest(Path(__file__).with_name("formats.py")),
            "validation_sha256": digest(Path(__file__).with_name("validation.py")),
            "experiments_sha256": digest(Path(__file__).with_name("experiments.py")),
            "environment": environment,
        }
    )
    result_path = output / "results.json"
    result = (
        json.loads(result_path.read_text(encoding="utf-8"))
        if result_path.exists()
        else {
            "version": 1,
            "identity": identity,
            "config": config,
            "tools": versions,
            "environment": environment,
            "samples": [],
            "trials": [],
            "screening": [],
            "skipped": [
                {
                    "encoder": name,
                    "reason": "No tested quality-control adapter; listed but not silently benchmarked",
                }
                for name in unknown
            ],
        }
    )
    if result["identity"] != identity:
        raise ValueError("Config, source content or toolchain changed. Use another output folder")
    for trial in result["trials"] + result["screening"]:
        if not Path(trial["output"]).is_file() or digest(Path(trial["output"])) != trial["sha256"]:
            raise ValueError("Cached output missing/modified; use a new output folder")
    started = time.monotonic()
    budget = float(config["budget_minutes"]) * 60
    stage = "tuning"
    tuning_budget = (
        budget * (1 - float(config.get("validation_reserve", 0.3)))
        if "validation_samples" in config
        else budget
    )
    deadline = tuning_budget

    def remaining() -> float:
        return max(0.1, deadline - (time.monotonic() - started))

    passes = 2 if config["mode"] == "quick" else 4
    targets = quality_targets(config)
    repeats = config.get("encode_repeats", 1)
    result["status"] = "running"
    result["stage"] = "validation" if "validation_shortlist" in result else "tuning"
    save(result_path, result)
    contexts: list[dict[str, Any]] = []
    searching = True

    def measure_candidate(encoder: str, quality: int) -> dict[str, Any]:
        nonlocal unscored_encodes
        key = f"{variant_id}-{stage}-{sample_id}-{encoder}-q{quality}"
        previous = next((t for t in result["trials"] if t["id"] == key), None)
        if previous:
            return previous
        if stage == "tuning" and plan["comparison"] == "initial":
            search_id = f"{variant_id}-{sample_id}-{encoder}"
            attempts = result.setdefault("initial_search_attempts", {})
            quota = max(
                1,
                plan["bounds"]["tuning_attempts"]
                // (len(config["samples"]) ** 2 * max(1, len(finalists))),
            )
            if searching and attempts.get(search_id, 0) >= quota:
                result["comparison_limit_reached"] = True
                raise ValueError(
                    "Initial per-encoder search bound reached; reserved work covers other encoders and scenes"
                )
            if result.get("initial_attempts", 0) >= plan["bounds"]["tuning_attempts"]:
                result["comparison_limit_reached"] = True
                raise ValueError(
                    "Initial comparison attempt bound reached; review evidence before explicitly expanding in a new configuration/output folder"
                )
            result["initial_attempts"] = result.get("initial_attempts", 0) + 1
            if searching:
                attempts[search_id] = attempts.get(search_id, 0) + 1
            save(result_path, result)
        print(
            f"[{sample_id}] {encoder} quality {quality}, shared {stage} measurement",
            flush=True,
        )
        trial_dir = directory / f"{encoder}-q{quality}"
        trial_dir.mkdir(exist_ok=True)
        temp = trial_dir / "encoded.partial.mkv"
        encoded = trial_dir / "encoded.mkv"
        # Uncheckpointed generated files are overwritten, never source files.
        probe_frames = min(video["frames"], max(2, round(float(Fraction(video["fps"])))))
        args = encode_args(
            ffmpeg,
            path,
            sample["start"],
            probe_frames,
            temp,
            encoder,
            quality,
            pixel,
            video,
            target,
        )
        pilot_started = time.monotonic()
        publish("pilot", current_candidate=key, measurement_stage=stage)
        run(args, min(30, remaining()))
        pilot_seconds = time.monotonic() - pilot_started
        validate_output(temp, target, encoder, pixel, ffprobe)
        publish(
            "pilot",
            pilot_estimate={
                "candidate": key,
                "seconds": pilot_seconds * video["frames"] / probe_frames,
                "note": "Actual one-second pilot extrapolation; approximate, includes startup, excludes scoring, references and other settings. No guaranteed total ETA.",
            },
        )
        print(
            f"  Pilot estimate: {pilot_seconds * video['frames'] / probe_frames:.0f}s for this sample (includes startup; approximate)",
            flush=True,
        )
        timings = []
        for repeat in range(repeats):
            if time.monotonic() - started >= deadline:
                raise subprocess.TimeoutExpired(encoder, budget)
            tick = time.monotonic()
            publish("encode", repeat=repeat + 1)
            run(
                encode_args(
                    ffmpeg,
                    path,
                    sample["start"],
                    video["frames"],
                    temp,
                    encoder,
                    quality,
                    pixel,
                    video,
                    target,
                ),
                remaining(),
            )
            timings.append(time.monotonic() - tick)
            unscored_encodes += 1
            publish("encode")
        validate_output(temp, target, encoder, pixel, ffprobe)
        publish("scoring")
        measured = score(
            ffmpeg,
            temp,
            reference,
            video,
            pixel,
            trial_dir,
            2 if config["mode"] == "quick" else 1,
            remaining(),
            ffprobe,
        )
        temp.replace(encoded)
        metrics = {
            "id": key,
            "sample": sample_id,
            "encoder": encoder,
            "variant": variant_id,
            "variant_label": variant["label"],
            "stage": stage,
            "quality": quality,
            "pixel_format": pixel,
            "width": target["width"],
            "height": target["height"],
            "resolution": config.get("resolution", "original"),
            "output": str(encoded),
            "sha256": digest(encoded),
            "bytes": encoded.stat().st_size,
            "encode_seconds": statistics.median(timings),
            "timings": timings,
            "preview": preview(ffmpeg, encoded, trial_dir / "preview.jpg"),
            **measured,
        }
        result["trials"].append(metrics)
        unscored_encodes -= len(timings)
        save(result_path, result)
        publish(stage)
        return metrics

    experiment_config = config
    variants = format_variants(config)
    print(f"Format combinations: {', '.join(v['label'] for v in variants)}", flush=True)
    print(
        f"Measured encodes per setting: {repeats} (tuning and validation; timing uses the median). Screening, pilots and different quality attempts are separate.",
        flush=True,
    )
    print(
        f"Compression tuning targets: VMAF {', '.join(str(t) for t in targets)}; shared measurements, not percentages of original quality.",
        flush=True,
    )
    print(
        f"Experiment plan: {json.dumps(plan)}. Cached settings are reused; exact adaptive remaining count is unknown.",
        flush=True,
    )
    for variant, index, sample in (
        (variant, index, sample)
        for variant in ([] if "validation_shortlist" in result else variants)
        for index, sample in enumerate(experiment_config["samples"])
    ):
        if time.monotonic() - started >= deadline:
            break
        config = {**experiment_config, **variant}
        variant_id = variant["id"]
        path = Path(sample["path"]).resolve()
        sample_id = f"sample-{index + 1}"
        directory = (
            output / variant_id / sample_id
            if "variants" in experiment_config
            else output / sample_id
        )
        directory.mkdir(parents=True, exist_ok=True)
        publish("reference", current_sample=sample_id, measurement_stage="tuning")
        try:
            video = inspect_source(path, float(sample["start"]), float(sample["seconds"]), ffprobe)
            target = output_video(video, config)
            pixel = target["pix_fmt"]
            reference_directory = output / sample_id
            reference_directory.mkdir(exist_ok=True)
            reference = reference_directory / "reference.mkv"
            frame_size = video["width"] * video["height"] * 4 * video["frames"]
            if (
                not reference.exists()
                and shutil.disk_usage(output).free < frame_size + 256 * 1024**2
            ):
                raise ValueError("Insufficient scratch space for a lossless reference")
            reference_identity = reference_directory / "reference.json"
            if reference.exists():
                if (
                    not reference_identity.exists()
                    or digest(reference) != json.loads(reference_identity.read_text())["sha256"]
                ):
                    raise ValueError("Cached reference is unverified or changed")
            else:
                temp_ref = reference_directory / "reference.partial.mkv"
                run(
                    [
                        ffmpeg,
                        "-v",
                        "error",
                        "-nostdin",
                        "-y",
                        "-ss",
                        str(sample["start"]),
                        "-i",
                        str(path),
                        "-map",
                        f"0:{video['index']}",
                        "-an",
                        "-frames:v",
                        str(video["frames"]),
                        "-c:v",
                        "ffv1",
                        "-level",
                        "3",
                        "-pix_fmt",
                        video["pix_fmt"],
                        *color_args(video),
                        str(temp_ref),
                    ],
                    remaining(),
                )
                temp_ref.replace(reference)
                save(reference_identity, {"sha256": digest(reference)})
            if not any(s["id"] == sample_id for s in result["samples"]):
                result["samples"].append(
                    {
                        "id": sample_id,
                        "source_id": f"source-{list(source_hashes).index(str(path)) + 1}",
                        "source_seconds": float(video["duration"]),
                        "stage": "tuning",
                        "label": sample.get("label", path.name),
                        "video": video,
                        "output_video": {
                            "width": target["width"],
                            "height": target["height"],
                            "pix_fmt": pixel,
                        },
                        "seconds": video["frames"] / float(Fraction(video["fps"])),
                        "original_bps": float(video.get("bit_rate", 0)),
                        "preview": preview(ffmpeg, reference, reference_directory / "original.jpg"),
                    }
                )
                save(result_path, result)
        except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            result["skipped"].append(
                {"sample": sample_id, "variant": variant_id, "reason": str(error)}
            )
            save(result_path, result)
            continue
        contexts.append(
            {
                "config": config,
                "variant": variant,
                "sample": sample,
                "video": video,
                "target": target,
                "reference": reference,
                "directory": directory,
                "path": path,
                "sample_id": sample_id,
                "variant_id": variant_id,
                "pixel": pixel,
            }
        )
        # Screen every configured installed implementation before spending the tuning budget.
        screen_frames = min(video["frames"], max(2, round(float(Fraction(video["fps"])))))
        screen_reference = directory / "screen-reference.mkv"
        try:
            run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-nostdin",
                    "-y",
                    "-i",
                    str(reference),
                    "-frames:v",
                    str(screen_frames),
                    "-c:v",
                    "ffv1",
                    "-pix_fmt",
                    video["pix_fmt"],
                    *color_args(video),
                    str(screen_reference),
                ],
                remaining(),
            )
        except subprocess.TimeoutExpired:
            break
        screen_video = {**video, "frames": screen_frames}
        for encoder in chosen:
            if time.monotonic() - started >= deadline:
                break
            if any(
                row["sample"] == sample_id
                and row.get("variant", "legacy") == variant_id
                and row["encoder"] == encoder
                for row in result["screening"]
            ):
                continue
            if encoder not in available:
                result["skipped"].append(
                    {
                        "sample": sample_id,
                        "variant": variant_id,
                        "encoder": encoder,
                        "reason": "Not present in FFmpeg build",
                    }
                )
                continue
            try:
                screen_dir = directory / (encoder + "-screen")
                screen_dir.mkdir(exist_ok=True)
                screen_output = screen_dir / "screen.mkv"
                quality = int(config.get("quality_overrides", {}).get(encoder, SPECS[encoder][1]))
                publish("screen", current_encoder=encoder)
                print(f"[{sample_id}] Compatibility/quality screen: {encoder}", flush=True)
                tick = time.monotonic()
                run(
                    encode_args(
                        ffmpeg,
                        path,
                        sample["start"],
                        screen_frames,
                        screen_output,
                        encoder,
                        quality,
                        pixel,
                        video,
                        target,
                    ),
                    min(30, remaining()),
                )
                elapsed = time.monotonic() - tick
                validate_output(screen_output, target, encoder, pixel, ffprobe)
                publish("scoring", measurement_stage="screen")
                measured = score(
                    ffmpeg,
                    screen_output,
                    screen_reference,
                    screen_video,
                    pixel,
                    screen_dir,
                    1,
                    remaining(),
                    ffprobe,
                )
                result["screening"].append(
                    {
                        "sample": sample_id,
                        "encoder": encoder,
                        "quality": quality,
                        "variant": variant_id,
                        "stage": "tuning",
                        "encode_seconds": elapsed,
                        "bytes": screen_output.stat().st_size,
                        "output": str(screen_output),
                        "sha256": digest(screen_output),
                        **measured,
                    }
                )
            except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                result["skipped"].append(
                    {
                        "sample": sample_id,
                        "encoder": encoder,
                        "reason": "Screen failed: " + str(error),
                        "variant": variant_id,
                    }
                )
            save(result_path, result)
            publish("screen", measurement_stage="tuning")
        screens = [
            row
            for row in result["screening"]
            if row["sample"] == sample_id and row.get("variant", "legacy") == variant_id
        ]
        # A short screen is only a heuristic: favor near-target quality, then storage/time.
        screens.sort(
            key=lambda row: (
                max(0, max(targets) - row["vmaf"]),
                row["bytes"],
                row["encode_seconds"],
            )
        )
        finalists = [row["encoder"] for row in screens[: 4 if config["mode"] == "quick" else 8]]
        for encoder, quality_target in ((e, t) for e in finalists for t in targets):
            if time.monotonic() - started >= deadline:
                break
            if encoder not in available:
                result["skipped"].append(
                    {
                        "sample": sample_id,
                        "variant": variant_id,
                        "encoder": encoder,
                        "reason": "Not present in FFmpeg build",
                    }
                )
                continue
            _, initial, low, high, _ = SPECS[encoder]
            tested = [
                (t["quality"], t["vmaf"])
                for t in result["trials"]
                if t.get("stage", "tuning") == "tuning"
                and t.get("variant", "legacy") == variant_id
                and t["sample"] == sample_id
                and t["encoder"] == encoder
            ]
            quality = (
                min(tested, key=lambda item: abs(item[1] - quality_target))[0]
                if tested
                else int(config.get("quality_overrides", {}).get(encoder, initial))
            )
            # Freeze the search seed so resuming cannot grant another round of attempts.
            search_key = f"{variant_id}-{sample_id}-{encoder}-{quality_target}"
            search = result.setdefault("tuning_searches", {}).setdefault(
                search_key, {"quality": quality, "known": tested}
            )
            quality, tested = search["quality"], list(search["known"])
            save(result_path, result)
            print(f"[{sample_id}] {encoder}: searching VMAF {quality_target}", flush=True)
            metrics: dict[str, Any]
            try:
                for attempt in range(passes):
                    key = f"{variant_id}-tuning-{sample_id}-{encoder}-q{quality}"
                    previous = next((t for t in result["trials"] if t["id"] == key), None)
                    if previous:
                        metrics = previous
                    else:
                        metrics = measure_candidate(encoder, quality)
                    if not any(q == quality for q, _ in tested):
                        tested.append((quality, metrics["vmaf"]))
                    difference = quality_target - metrics["vmaf"]
                    if -float(config.get("tolerance", 0.5)) <= difference <= 0:
                        break
                    direction = 1 if encoder.endswith("_videotoolbox") else -1
                    step = max(1, min(8, round(abs(difference) * 2)))
                    quality = max(
                        low, min(high, quality + direction * (step if difference > 0 else -step))
                    )
                    below = [(q, v) for q, v in tested if v < quality_target]
                    above = [(q, v) for q, v in tested if v >= quality_target]
                    if below and above:
                        a = min(below, key=lambda item: abs(item[1] - quality_target))[0]
                        b = min(above, key=lambda item: abs(item[1] - quality_target))[0]
                        quality = (a + b) // 2
                    if any(q == quality for q, _ in tested):
                        break
            except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                result["skipped"].append(
                    {
                        "sample": sample_id,
                        "variant": variant_id,
                        "encoder": encoder,
                        "reason": str(error),
                    }
                )
                save(result_path, result)
        if time.monotonic() - started >= deadline:
            break
    # Independently tuned qualities are candidates, not per-scene winners. Fill their missing evidence.
    candidates = sorted(
        {(t.get("variant", "legacy"), t["encoder"], t["quality"]) for t in result["trials"]}
    )
    searching = False
    for context in contexts:
        config, variant, sample = context["config"], context["variant"], context["sample"]
        video, target, reference = context["video"], context["target"], context["reference"]
        directory, path = context["directory"], context["path"]
        sample_id, variant_id, pixel = context["sample_id"], context["variant_id"], context["pixel"]
        for candidate_variant, encoder, quality in candidates:
            if candidate_variant != variant_id:
                continue
            if time.monotonic() - started >= deadline:
                break
            try:
                measure_candidate(encoder, quality)
            except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                result["skipped"].append(
                    {
                        "sample": sample_id,
                        "variant": variant_id,
                        "encoder": encoder,
                        "quality": quality,
                        "stage": "tuning",
                        "reason": str(error),
                    }
                )
                save(result_path, result)
    config = experiment_config
    if "validation_samples" in config:
        if "validation_shortlist" not in result:
            selected = shortlist(result)
            if selected:
                result["validation_shortlist"] = selected
            result["validation_target"] = config.get("target_vmaf", max(targets))
            result["validation_targets"] = targets
        result["validation_required"] = len(source_hashes)
        result["validation_reserve"] = config.get("validation_reserve", 0.3)
        result["budget_scope"] = "per invocation, shared across all stages and variants"
        result["stage"] = "validation"
        publish(
            "validation",
            frozen_validation_trials=len(result.get("validation_shortlist", []))
            * len(config["validation_samples"]),
        )
        save(result_path, result)
        stage, deadline = "validation", budget
        for candidate in result.get("validation_shortlist", []):
            for index, sample in enumerate(config["validation_samples"]):
                if time.monotonic() - started >= deadline:
                    break
                variant = next(v for v in variants if v["id"] == candidate["variant"])
                variant_id = variant["id"]
                sample_id = f"validation-{index + 1}"
                path = Path(sample["path"]).resolve()
                directory = output / variant_id / sample_id
                directory.mkdir(parents=True, exist_ok=True)
                if any(
                    failure.get("stage") == stage
                    and failure.get("sample") == sample_id
                    and failure.get("variant") == variant_id
                    and failure.get("encoder") == candidate["encoder"]
                    and failure.get("quality") == candidate["quality"]
                    and failure.get("terminal")
                    for failure in result["skipped"]
                ):
                    continue
                try:
                    publish("reference", current_sample=sample_id, measurement_stage="validation")
                    video = inspect_source(
                        path, float(sample["start"]), float(sample["seconds"]), ffprobe
                    )
                    target = output_video(video, variant)
                    pixel = target["pix_fmt"]
                    reference_directory = output / sample_id
                    reference_directory.mkdir(exist_ok=True)
                    reference = reference_directory / "reference.mkv"
                    reference_identity = reference_directory / "reference.json"
                    if reference.exists():
                        if (
                            not reference_identity.exists()
                            or digest(reference)
                            != json.loads(reference_identity.read_text())["sha256"]
                        ):
                            raise ValueError("Cached validation reference is unverified or changed")
                    else:
                        if (
                            shutil.disk_usage(output).free
                            < video["width"] * video["height"] * 4 * video["frames"] + 256 * 1024**2
                        ):
                            raise ValueError("Insufficient scratch space for validation reference")
                        temp_ref = reference_directory / "reference.partial.mkv"
                        run(
                            [
                                ffmpeg,
                                "-v",
                                "error",
                                "-nostdin",
                                "-y",
                                "-ss",
                                str(sample["start"]),
                                "-i",
                                str(path),
                                "-map",
                                f"0:{video['index']}",
                                "-an",
                                "-frames:v",
                                str(video["frames"]),
                                "-c:v",
                                "ffv1",
                                "-level",
                                "3",
                                "-pix_fmt",
                                video["pix_fmt"],
                                *color_args(video),
                                str(temp_ref),
                            ],
                            remaining(),
                        )
                        temp_ref.replace(reference)
                        save(reference_identity, {"sha256": digest(reference)})
                    if not any(s["id"] == sample_id for s in result["samples"]):
                        result["samples"].append(
                            {
                                "id": sample_id,
                                "source_id": f"source-{list(source_hashes).index(str(path)) + 1}",
                                "source_seconds": video["duration"],
                                "stage": stage,
                                "label": sample.get("label", path.name),
                                "start": sample["start"],
                                "seconds": video["frames"] / float(Fraction(video["fps"])),
                                "video": video,
                                "preview": preview(
                                    ffmpeg, reference, reference_directory / "original.jpg"
                                ),
                            }
                        )
                    config = {**experiment_config, **variant}
                    measure_candidate(candidate["encoder"], candidate["quality"])
                except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                    result["skipped"].append(
                        {
                            "sample": sample_id,
                            "variant": variant_id,
                            "encoder": candidate["encoder"],
                            "quality": candidate["quality"],
                            "stage": stage,
                            "terminal": not isinstance(error, subprocess.TimeoutExpired),
                            "reason": str(error),
                        }
                    )
                    save(result_path, result)
        config = experiment_config
        for candidate in result.get("validation_shortlist", []):
            evidence = [
                t
                for t in result["trials"]
                if t.get("stage") == "validation"
                and t["variant"] == candidate["variant"]
                and t["encoder"] == candidate["encoder"]
                and t["quality"] == candidate["quality"]
            ]
            terminal = any(
                s.get("stage") == "validation"
                and s.get("variant") == candidate["variant"]
                and s.get("encoder") == candidate["encoder"]
                and s.get("quality") == candidate["quality"]
                and s.get("terminal")
                for s in result["skipped"]
            )
            complete = {t["sample"] for t in evidence} == {
                f"validation-{i + 1}" for i in range(result["validation_required"])
            }
            candidate["target_statuses"] = {
                str(quality_target): (
                    "failed"
                    if terminal or any(t["vmaf"] < quality_target for t in evidence)
                    else "validated"
                    if complete
                    else "incomplete"
                )
                for quality_target in candidate.get("targets", [result["validation_target"]])
            }
            candidate["evidence_status"] = candidate["target_statuses"][
                str(min(candidate.get("targets", [result["validation_target"]])))
            ]
            candidate["validation_coverage"] = len(evidence)
        result["validation_status"] = (
            "validated"
            if any(
                c["evidence_status"] == "validated" for c in result.get("validation_shortlist", [])
            )
            else "incomplete"
            if any(
                c["evidence_status"] == "incomplete" for c in result.get("validation_shortlist", [])
            )
            else "failed"
            if result.get("validation_shortlist")
            else "no qualifying tuning candidates"
        )
    from .stills import generate_stills
    from .media import generate_review_media

    publish("review_generation")
    generate_stills(result, output, remaining)
    generate_review_media(result, output, remaining)
    result["status"] = "budget_exhausted" if time.monotonic() - started >= deadline else "completed"
    result["session_seconds"] = time.monotonic() - started
    result["remaining_seconds"] = max(0, budget - result["session_seconds"])
    save(result_path, result)
    publish(
        "finished",
        status=result["status"],
        comparison_limit_reached=result.get("comparison_limit_reached", False),
        validation_status=result.get("validation_status", "unavailable"),
    )
    return result
