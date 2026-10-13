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
from .formats import output_video, scale_filter, validate_formats


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
    if not config.get("samples"):
        raise ValueError("Select at least one sample")
    validate_formats(config)
    if not 0 < float(config.get("target_vmaf", 95)) <= 100:
        raise ValueError("VMAF target must be in (0,100]")
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
    if not 0 <= float(config.get("tolerance", 0.5)) <= 5:
        raise ValueError("VMAF tolerance must be between 0 and 5")
    for name, quality in config.get("quality_overrides", {}).items():
        options(
            name,
            int(quality),
            "yuv420p" if config["pixel_format"] == "source" else config["pixel_format"],
        )


def benchmark(config_path: Path, output: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_config(config)
    output = output.resolve()
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
            return result
    finally:
        lock.unlink(missing_ok=True)


def _benchmark(config: dict[str, Any], output: Path) -> dict[str, Any]:
    import platform
    import shutil

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
    source_hashes = {
        str(Path(s["path"]).resolve()): digest(Path(s["path"])) for s in config["samples"]
    }
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
            "environment": environment,
        }
    )
    result_path = output / "results.json"
    result: dict[str, Any] = (
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

    def remaining() -> float:
        return max(0.1, budget - (time.monotonic() - started))

    passes = 2 if config["mode"] == "quick" else 4
    repeats = 1 if config["mode"] == "quick" else 3
    result["status"] = "running"
    save(result_path, result)
    for index, sample in enumerate(config["samples"]):
        path = Path(sample["path"]).resolve()
        sample_id = f"sample-{index + 1}"
        directory = output / sample_id
        directory.mkdir(exist_ok=True)
        try:
            video = inspect_source(path, float(sample["start"]), float(sample["seconds"]), ffprobe)
            target = output_video(video, config)
            pixel = target["pix_fmt"]
            reference = directory / "reference.mkv"
            frame_size = video["width"] * video["height"] * 4 * video["frames"]
            if (
                not reference.exists()
                and shutil.disk_usage(output).free < frame_size + 256 * 1024**2
            ):
                raise ValueError("Insufficient scratch space for a lossless reference")
            reference_identity = directory / "reference.json"
            if reference.exists():
                if (
                    not reference_identity.exists()
                    or digest(reference) != json.loads(reference_identity.read_text())["sha256"]
                ):
                    raise ValueError("Cached reference is unverified or changed")
            else:
                temp_ref = directory / "reference.partial.mkv"
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
                        "label": sample.get("label", path.name),
                        "video": video,
                        "output_video": {
                            "width": target["width"],
                            "height": target["height"],
                            "pix_fmt": pixel,
                        },
                        "seconds": video["frames"] / float(Fraction(video["fps"])),
                        "original_bps": float(video.get("bit_rate", 0)),
                        "preview": preview(ffmpeg, reference, directory / "original.jpg"),
                    }
                )
                save(result_path, result)
        except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            result["skipped"].append({"sample": sample_id, "reason": str(error)})
            save(result_path, result)
            continue
        # Screen every configured installed implementation before spending the tuning budget.
        screen_frames = min(video["frames"], max(2, round(float(Fraction(video["fps"])))))
        screen_reference = directory / "screen-reference.mkv"
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
        screen_video = {**video, "frames": screen_frames}
        for encoder in chosen:
            if time.monotonic() - started >= budget:
                break
            if any(
                row["sample"] == sample_id and row["encoder"] == encoder
                for row in result["screening"]
            ):
                continue
            if encoder not in available:
                result["skipped"].append(
                    {
                        "sample": sample_id,
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
                    }
                )
            save(result_path, result)
        screens = [row for row in result["screening"] if row["sample"] == sample_id]
        # A short screen is only a heuristic: favor near-target quality, then storage/time.
        screens.sort(
            key=lambda row: (
                max(0, float(config["target_vmaf"]) - row["vmaf"]),
                row["bytes"],
                row["encode_seconds"],
            )
        )
        finalists = [row["encoder"] for row in screens[: 4 if config["mode"] == "quick" else 8]]
        for encoder in finalists:
            if time.monotonic() - started >= budget:
                break
            if encoder not in available:
                result["skipped"].append(
                    {
                        "sample": sample_id,
                        "encoder": encoder,
                        "reason": "Not present in FFmpeg build",
                    }
                )
                continue
            _, initial, low, high, _ = SPECS[encoder]
            quality = int(config.get("quality_overrides", {}).get(encoder, initial))
            tested: list[tuple[int, float]] = []
            metrics: dict[str, Any]
            try:
                for attempt in range(passes):
                    key = f"{sample_id}-{encoder}-q{quality}"
                    previous = next((t for t in result["trials"] if t["id"] == key), None)
                    if previous:
                        metrics = previous
                    else:
                        print(
                            f"[{sample_id}] {encoder} quality {quality}, trial {attempt + 1}/{passes}",
                            flush=True,
                        )
                        trial_dir = directory / f"{encoder}-q{quality}"
                        trial_dir.mkdir(exist_ok=True)
                        temp = trial_dir / "encoded.partial.mkv"
                        encoded = trial_dir / "encoded.mkv"
                        # Uncheckpointed generated files are overwritten, never source files.
                        probe_frames = min(
                            video["frames"], max(2, round(float(Fraction(video["fps"]))))
                        )
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
                        run(args, min(30, remaining()))
                        pilot_seconds = time.monotonic() - pilot_started
                        validate_output(temp, target, encoder, pixel, ffprobe)
                        print(
                            f"  Pilot estimate: {pilot_seconds * video['frames'] / probe_frames:.0f}s for this sample (includes startup; approximate)",
                            flush=True,
                        )
                        timings = []
                        for repeat in range(repeats):
                            if time.monotonic() - started >= budget:
                                raise subprocess.TimeoutExpired(encoder, budget)
                            tick = time.monotonic()
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
                        validate_output(temp, target, encoder, pixel, ffprobe)
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
                        save(result_path, result)
                    tested.append((quality, metrics["vmaf"]))
                    difference = float(config["target_vmaf"]) - metrics["vmaf"]
                    if abs(difference) <= float(config.get("tolerance", 0.5)):
                        break
                    direction = 1 if encoder.endswith("_videotoolbox") else -1
                    step = max(1, min(8, round(abs(difference) * 2)))
                    quality = max(
                        low, min(high, quality + direction * (step if difference > 0 else -step))
                    )
                    if any(q == quality for q, _ in tested):
                        break
            except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                result["skipped"].append(
                    {"sample": sample_id, "encoder": encoder, "reason": str(error)}
                )
                save(result_path, result)
        if time.monotonic() - started >= budget:
            break
    result["status"] = "budget_exhausted" if time.monotonic() - started >= budget else "completed"
    result["session_seconds"] = time.monotonic() - started
    save(result_path, result)
    return result
