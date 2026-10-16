"""Budgeted fixed-setting comparisons; quality is measured, never targeted."""

import json
import os
import platform
import shutil
import statistics
import subprocess
import time
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import core
from .budget import deadline
from .encoders import SPECS
from .experiments import experiment_plan, fixed_settings
from .formats import format_variants, output_video


def frontier(rows: list[dict[str, Any]]) -> set[tuple[str, str, int]]:
    """Only compare settings on the same scene and format."""
    return {
        (row["variant"], row["encoder"], row["quality"])
        for row in rows
        if not any(
            other["variant"] == row["variant"]
            and other["sample"] == row["sample"]
            and other["bytes"] <= row["bytes"]
            and other["encode_seconds"] <= row["encode_seconds"]
            and other["vmaf"] >= row["vmaf"]
            and (
                other["bytes"] < row["bytes"]
                or other["encode_seconds"] < row["encode_seconds"]
                or other["vmaf"] > row["vmaf"]
            )
            for other in rows
        )
    }


def work_items(config: dict[str, Any]) -> list[dict[str, Any]]:
    settings = fixed_settings(config)
    # Round-robin qualities puts CPU/GPU comparisons before a second setting.
    return [
        {
            "id": f"{variant['id']}-tuning-sample-{index + 1}-{encoder}-q{quality}",
            "sample": f"sample-{index + 1}",
            "variant": variant["id"],
            "encoder": encoder,
            "quality": quality,
            "status": "pending",
            "estimated_seconds": None,
        }
        for index, _ in enumerate(config["samples"])
        for variant in format_variants(config)
        for position in range(max(map(len, settings.values())))
        for encoder, values in settings.items()
        for quality in values[position : position + 1]
    ]


def benchmark_fixed(config: dict[str, Any], output: Path) -> dict[str, Any]:
    started = time.monotonic()
    if config.get("review_mode", "deferred") not in ("deferred", "full"):
        raise ValueError("review_mode must be deferred or full")
    budget = float(config.get("budget_minutes", 0)) * 60
    if not 0 < budget < float("inf"):
        raise ValueError("Set a positive finite time budget")
    output = output.resolve()
    if any(Path(s["path"]).resolve().is_relative_to(output) for s in config["samples"]):
        raise ValueError("Run output folder contains a selected source")
    output.mkdir(parents=True, exist_ok=True)
    lock = output / ".lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    end = started + budget
    reserve = min(60, budget * 0.15)
    work_end = end - reserve
    token = deadline.set(work_end)
    result_path = output / "results.json"
    can_save = not result_path.exists()
    result: dict[str, Any] = {
        "version": 1,
        "identity": None,
        "config": config,
        "tools": {},
        "environment": {},
        "samples": [],
        "trials": [],
        "screening": [],
        "skipped": [],
        "status": "running",
        "work": work_items(config),
        "strategy": "fixed",
        "validation_status": "not requested; measured starting points",
        "timing_scope": "Sequential measured encodes; no competing benchmark encodes or scoring. Encoder automatic threading; CPU available to benchmark. Quality controls do not change during a trial.",
        "budget_scope": "wall clock including preparation, scoring and review/report; final writes and process cleanup may slightly overrun",
    }
    progress: dict[str, Any] = {"status": "running", "stage": "initialization", "stages_seen": []}

    def publish(stage: str, **details: Any) -> None:
        progress.update(details)
        progress.update(
            stage=stage,
            status=result["status"],
            completed_trials=len(result["trials"]),
            updated_at=datetime.now(timezone.utc).isoformat(),
            elapsed_seconds=time.monotonic() - started,
            remaining_seconds=max(0, end - time.monotonic()),
        )
        if stage not in progress["stages_seen"]:
            progress["stages_seen"].append(stage)
        for item in result["work"]:
            if item["status"] != "pending":
                continue
            timings = [
                t["work_seconds"]
                / next(s["seconds"] for s in result["samples"] if s["id"] == t["sample"])
                for t in result["trials"]
                if t["encoder"] == item["encoder"] and t["variant"] == item["variant"]
            ]
            seconds = config["samples"][int(item["sample"].split("-")[-1]) - 1]["seconds"]
            item["estimated_seconds"] = statistics.mean(timings) * seconds if timings else None
        pending = [w for w in result["work"] if w["status"] == "pending"]
        progress["remaining_work"] = len(pending)
        progress["estimated_remaining_seconds"] = (
            sum(w["estimated_seconds"] for w in pending)
            if all(w["estimated_seconds"] is not None for w in pending)
            else None
        )
        progress["estimate_note"] = (
            "Measured per-encoder/format work extrapolation; new-scene preparation and content can change it. Unknown work remains unknown."
        )
        if can_save:
            core.save(result_path, result)
        core.save(output / "progress.json", progress)

    try:
        if result_path.exists():
            result = json.loads(result_path.read_text(encoding="utf-8"))
            if result["config"] != config:
                raise ValueError("Config changed; use a new output folder")
            can_save = result["identity"] is None
            result["status"] = "running"
        publish("initialization")
        try:
            core.validate_config(config)
            ffmpeg, ffprobe = config.get("ffmpeg", "ffmpeg"), config.get("ffprobe", "ffprobe")
            versions = {}
            for name, executable in [("ffmpeg", ffmpeg), ("ffprobe", ffprobe)]:
                located = shutil.which(str(executable))
                if not located:
                    raise ValueError(f"Missing executable: {executable}")
                versions[name] = {
                    "version": core.run([executable, "-version"]),
                    "sha256": core.digest(Path(located)),
                }
            if "libvmaf" not in core.run([ffmpeg, "-filters"]):
                raise ValueError("FFmpeg must include libvmaf")
            sources = {}
            for sample in config["samples"]:
                path = Path(sample["path"]).resolve()
                if str(path) not in sources:
                    publish("hashing", current_source=path.name)
                    sources[str(path)] = core.digest(path)
            environment = {
                "platform": platform.platform(),
                "cpu": platform.processor(),
                "logical_cpus": os.cpu_count(),
            }
            if shutil.which("nvidia-smi"):
                environment["nvidia_gpu_driver_memory"] = core.run(
                    [
                        "nvidia-smi",
                        "--query-gpu=name,driver_version,memory.total",
                        "--format=csv,noheader,nounits",
                    ],
                    10,
                ).strip()
            identity = core.fingerprint(
                {
                    "config": config,
                    "sources": sources,
                    "tools": versions,
                    "environment": environment,
                    "adapters": SPECS,
                    "code": {
                        name: core.digest(Path(__file__).with_name(name))
                        for name in (
                            "core.py",
                            "fixed.py",
                            "budget.py",
                            "encoders.py",
                            "formats.py",
                            "experiments.py",
                        )
                    },
                }
            )
            if result["identity"] not in (None, identity):
                raise ValueError("Source/toolchain changed; use a new output folder")
            result.update(identity=identity, tools=versions, environment=environment)
            for trial in result["trials"]:
                if (
                    not Path(trial["output"]).is_file()
                    or core.digest(Path(trial["output"])) != trial["sha256"]
                ):
                    raise ValueError("Cached output missing/modified; use a new output folder")
            can_save = True
            print(json.dumps(experiment_plan(config)), flush=True)
            contexts = {}
            blocked = set()
            for item in result["work"]:
                if item["status"] != "pending":
                    continue
                if time.monotonic() >= work_end:
                    break
                if item["sample"] != "sample-1" and (
                    item["variant"],
                    item["encoder"],
                    item["quality"],
                ) not in frontier([t for t in result["trials"] if t["sample"] == "sample-1"]):
                    item.update(
                        status="not selected",
                        reason="Not on first-scene measured frontier, or first-scene evidence missing",
                    )
                    continue
                key = (item["sample"], item["variant"], item["encoder"])
                if key in blocked:
                    item.update(
                        status="failed", reason="Earlier encode failed requested format checks"
                    )
                    continue
                estimate = item["estimated_seconds"]
                if estimate is not None and estimate * 1.15 > work_end - time.monotonic():
                    item["reason"] = "Estimated work does not fit remaining allowance"
                    continue
                publish("preparation", current_candidate=item["id"])
                tick = time.monotonic()
                pending_count = sum(
                    w["status"] == "pending" and w["sample"] == item["sample"]
                    for w in result["work"]
                )
                item["attempt_allowance_seconds"] = max(
                    0.1, (work_end - tick) / max(1, pending_count)
                )
                deadline.set(min(work_end, tick + item["attempt_allowance_seconds"]))
                try:
                    index = int(item["sample"].split("-")[-1]) - 1
                    sample = config["samples"][index]
                    path = Path(sample["path"]).resolve()
                    reference_dir = output / item["sample"]
                    reference_dir.mkdir(exist_ok=True)
                    reference = reference_dir / "reference.mkv"
                    if item["sample"] not in contexts:
                        video = core.inspect_source(
                            path, sample["start"], sample["seconds"], ffprobe
                        )
                        record = reference_dir / "reference.json"
                        if reference.exists():
                            if (
                                not record.exists()
                                or core.digest(reference)
                                != json.loads(record.read_text())["sha256"]
                            ):
                                raise ValueError("Cached reference missing/modified")
                        else:
                            if (
                                shutil.disk_usage(output).free
                                < video["width"] * video["height"] * 4 * video["frames"]
                                + 256 * 1024**2
                            ):
                                raise ValueError("Insufficient scratch space")
                            temporary = reference_dir / "reference.partial.mkv"
                            core.run(
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
                                    *core.color_args(video),
                                    str(temporary),
                                ],
                                work_end - time.monotonic(),
                            )
                            temporary.replace(reference)
                            core.save(record, {"sha256": core.digest(reference)})
                        contexts[item["sample"]] = video
                        if not any(s["id"] == item["sample"] for s in result["samples"]):
                            result["samples"].append(
                                {
                                    "id": item["sample"],
                                    "source_id": f"source-{list(sources).index(str(path)) + 1}",
                                    "source_seconds": video["duration"],
                                    "stage": "tuning",
                                    "label": sample.get("label", path.name),
                                    "start": sample["start"],
                                    "seconds": video["frames"] / float(Fraction(video["fps"])),
                                    "video": video,
                                    "original_bps": float(video.get("bit_rate", 0)),
                                    "preview": core.preview(
                                        ffmpeg, reference, reference_dir / "original.jpg"
                                    ),
                                }
                            )
                    video = contexts[item["sample"]]
                    variant = next(v for v in format_variants(config) if v["id"] == item["variant"])
                    target = output_video(video, variant)
                    directory = (
                        output
                        / item["variant"]
                        / item["sample"]
                        / f"{item['encoder']}-q{item['quality']}"
                    )
                    directory.mkdir(parents=True, exist_ok=True)
                    temporary = directory / "encoded.partial.mkv"
                    encoded = directory / "encoded.mkv"
                    preparation = time.monotonic() - tick
                    timings = []
                    for _ in range(config.get("encode_repeats", 1)):
                        publish("encode")
                        print(f"{item['id']}: fixed encode", flush=True)
                        encode_start = time.monotonic()
                        core.run(
                            core.encode_args(
                                ffmpeg,
                                path,
                                sample["start"],
                                video["frames"],
                                temporary,
                                item["encoder"],
                                item["quality"],
                                target["pix_fmt"],
                                video,
                                target,
                            ),
                            work_end - time.monotonic(),
                        )
                        timings.append(time.monotonic() - encode_start)
                    core.validate_output(
                        temporary, target, item["encoder"], target["pix_fmt"], ffprobe
                    )
                    publish("scoring")
                    scoring_start = time.monotonic()
                    threads = result.get("scoring_threads", os.cpu_count() or 1)
                    measured = core.score(
                        ffmpeg,
                        temporary,
                        reference,
                        video,
                        target["pix_fmt"],
                        directory,
                        1,
                        work_end - time.monotonic(),
                        ffprobe,
                        threads=threads,
                    )
                    scoring_seconds = time.monotonic() - scoring_start
                    # A bounded second scoring measurement calibrates parallelism without re-encoding.
                    if "scoring_threads" not in result:
                        result["scoring_threads"] = threads
                        result["thread_calibration"] = [
                            {"threads": threads, "seconds": scoring_seconds}
                        ]
                        if (
                            threads > 4
                            and scoring_seconds < min(15, budget * 0.02)
                            and work_end - time.monotonic() > scoring_seconds * 3
                        ):
                            calibration_start = time.monotonic()
                            try:
                                core.score(
                                    ffmpeg,
                                    temporary,
                                    reference,
                                    video,
                                    target["pix_fmt"],
                                    directory,
                                    1,
                                    min(15, budget * 0.02),
                                    ffprobe,
                                    threads=4,
                                )
                                elapsed = time.monotonic() - calibration_start
                                result["thread_calibration"].append(
                                    {"threads": 4, "seconds": elapsed}
                                )
                                if elapsed < scoring_seconds:
                                    result["scoring_threads"] = 4
                            except subprocess.TimeoutExpired:
                                result["thread_calibration"].append(
                                    {"threads": 4, "status": "calibration timeout"}
                                )
                    temporary.replace(encoded)
                    trial = {
                        **{k: item[k] for k in ("id", "sample", "variant", "encoder", "quality")},
                        "stage": "tuning",
                        "variant_label": variant["label"],
                        "pixel_format": target["pix_fmt"],
                        "width": target["width"],
                        "height": target["height"],
                        "resolution": variant["resolution"],
                        "output": str(encoded),
                        "sha256": core.digest(encoded),
                        "bytes": encoded.stat().st_size,
                        "encode_seconds": statistics.median(timings),
                        "timings": timings,
                        "preparation_seconds": preparation,
                        "scoring_seconds": scoring_seconds,
                        "scoring_threads": threads,
                        "preview": core.preview(ffmpeg, encoded, directory / "preview.jpg"),
                        **measured,
                    }
                    trial["work_seconds"] = time.monotonic() - tick
                    result["trials"].append(trial)
                    item["status"] = "completed"
                except subprocess.TimeoutExpired:
                    item["reason"] = (
                        "Attempt allowance exhausted; remaining encoders keep their share. Explicit resume can retry unfinished work."
                    )
                except (ValueError, RuntimeError) as error:
                    item.update(status="failed", reason=str(error))
                    result["skipped"].append({**item, "stage": "tuning"})
                    if "preserve requested" in str(error) or "No capable devices" in str(error):
                        blocked.add(key)
                finally:
                    deadline.set(work_end)
                publish("comparison")
        except subprocess.TimeoutExpired:
            result["status"] = "budget_exhausted"
            if not can_save:
                publish("verification_budget_exhausted")
                return result
        result["status"] = (
            "budget_exhausted"
            if any(w["status"] == "pending" for w in result["work"])
            else "completed"
        )
        deadline.set(end - min(5, reserve / 3))
        result["review_candidates"] = [
            {"variant": v, "encoder": e, "quality": q} for v, e, q in frontier(result["trials"])
        ]
        result["measurements_seconds"] = time.monotonic() - started
        result["review_note"] = (
            "Detailed browser review deferred. Use review prepare --trial ID, or native review launch."
        )
        publish("report_ready")
        from .report import write_report

        write_report(result, output)
        print(f"Measurements report ready: {output / 'report.html'}", flush=True)
        from .stills import generate_stills
        from .media import generate_review_media

        def remaining() -> float:
            return max(0, end - min(5, reserve / 3) - time.monotonic())

        try:
            review_started = time.monotonic()
            if config.get("review_mode", "deferred") == "full":
                publish("review_generation")
                result["review_note"] = "Full browser review requested; inspect asset statuses."
                generate_stills(result, output, remaining)
                generate_review_media(result, output, remaining)
            result["review_seconds"] = time.monotonic() - review_started
        except subprocess.TimeoutExpired:
            result["review_note"] = (
                "Review assets incomplete within budget; exact encoded files remain available"
            )
        result["session_seconds"] = time.monotonic() - started
        publish("finished")
        # File-only report generation must still deliver partial results after a deadline.
        deadline.set(None)
        from .report import write_report

        write_report(result, output)
        result["session_seconds"] = time.monotonic() - started
        result["budget_overrun_seconds"] = max(0, result["session_seconds"] - budget)
        core.save(result_path, result)
        return result
    except (ValueError, RuntimeError, OSError, KeyboardInterrupt) as error:
        result["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
        progress["error"] = str(error)
        # A failed identity check must never rewrite prior canonical evidence.
        core.save(output / "progress.json", {**progress, "status": result["status"]})
        raise
    finally:
        deadline.reset(token)
        lock.unlink(missing_ok=True)
