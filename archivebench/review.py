"""Exact-clip review and user attestations, separate from metric evidence."""

import json
import math
import shutil
import subprocess
import time
import os
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

from .core import digest, run, save


CAVEATS = (
    "User visual attestation, not an automated quality pass. Native viewer uses exact files; "
    "automatic filters and tone mapping are disabled. Display scaling and YUV/RGB conversion "
    "still occur. Log/HDR needs an appropriate independently checked viewing transform. "
    "Default display is 8-bit; requesting 10-bit does not verify monitor/driver fidelity. "
    "Browser previews are converted 8-bit aids. Audio needs separate review; video-compare is silent."
)


def prepare_review(directory: Path, trial_id: str, seconds: float = 120) -> dict[str, Any]:
    """Prepare one selected trial without repeating benchmark measurements."""
    from .budget import deadline
    from .media import generate_review_media
    from .stills import generate_stills
    from .report import write_report

    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("Review allowance must be positive and finite")
    root = directory.resolve()
    lock = root / ".lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    started = time.monotonic()
    end = started + seconds
    token = deadline.set(end)
    try:
        inspect_review(root, trial_id)
        result = json.loads((root / "results.json").read_text(encoding="utf-8"))
        trial = next(t for t in result["trials"] if t["id"] == trial_id)
        selected = {
            **result,
            "trials": [trial],
            "validation_shortlist": [],
            "review_candidates": [{k: trial[k] for k in ("variant", "encoder", "quality")}],
        }

        def remaining() -> float:
            return max(0, end - time.monotonic())

        generate_stills(selected, root, remaining)
        generate_review_media(selected, root, remaining)
        elapsed = time.monotonic() - started
        result.setdefault("review_sessions", []).append({"trial": trial_id, "seconds": elapsed})
        save(root / "results.json", result)
        deadline.set(None)
        write_report(result, root)
        return {
            "trial": trial_id,
            "seconds": elapsed,
            "stills": trial.get("review_stills", {}).get("status", "incomplete"),
            "media": trial.get("review_media", {}).get("status", "unavailable"),
            "report": str(root / "report.html"),
        }
    finally:
        deadline.reset(token)
        lock.unlink(missing_ok=True)


def inspect_review(directory: Path, trial_id: str) -> dict[str, Any]:
    root = directory.resolve()
    result = json.loads((root / "results.json").read_text(encoding="utf-8"))
    trials = [trial for trial in result["trials"] if trial["id"] == trial_id]
    if len(trials) != 1:
        raise ValueError("Choose one exact measured trial id")
    trial = trials[0]
    sample = next(item for item in result["samples"] if item["id"] == trial["sample"])

    def bounded(path: Path) -> Path:
        value = path.resolve()
        if not value.is_relative_to(root):
            raise ValueError("Review media outside benchmark directory")
        if not value.is_file():
            raise ValueError("Exact review media missing; browser report remains available")
        return value

    reference = bounded(root / sample["id"] / "reference.mkv")
    candidate = bounded(Path(trial["output"]))
    reference_sha = json.loads(reference.with_name("reference.json").read_text())["sha256"]
    if digest(reference) != reference_sha or digest(candidate) != trial["sha256"]:
        raise ValueError("Review media changed; prior decisions are invalid")
    start = sample.get("start")
    if start is None and sample["id"].startswith("sample-"):
        index = int(sample["id"].split("-")[-1]) - 1
        start = result["config"]["samples"][index]["start"]
    if start is None:
        raise ValueError("Reviewed source interval unavailable")
    return {
        "benchmark_identity": result["identity"],
        "trial": trial_id,
        "source_id": sample.get("source_id", sample["id"]),
        "interval": {"start": float(start), "seconds": float(sample["seconds"])},
        "reference": {"path": str(reference), "sha256": reference_sha},
        "candidate": {"path": str(candidate), "sha256": trial["sha256"]},
        "caveats": CAVEATS,
    }


def decoded_alignment(pair: dict[str, Any], ffprobe: str = "ffprobe") -> dict[str, Any]:
    videos = []
    timelines = []
    for key in ("reference", "candidate"):
        info = json.loads(
            run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_streams",
                    "-show_frames",
                    "-of",
                    "json",
                    pair[key]["path"],
                ]
            )
        )
        stream = info["streams"][0]
        frames = info["frames"]
        times = [float(frame["best_effort_timestamp_time"]) for frame in frames]
        if not frames or any(
            frame["width"] != stream["width"] or frame["height"] != stream["height"]
            for frame in frames
        ):
            raise ValueError("Decoded dimensions change within reviewed clip")
        videos.append(
            {
                key: stream.get(key)
                for key in (
                    "width",
                    "height",
                    "pix_fmt",
                    "avg_frame_rate",
                    "color_range",
                    "color_space",
                    "color_transfer",
                    "color_primaries",
                )
            }
        )
        timelines.append(times)
    fps = float(Fraction(videos[0]["avg_frame_rate"]))
    if (
        fps <= 0
        or len(timelines[0]) != len(timelines[1])
        or any(abs(left - right) > 0.5 / fps for left, right in zip(timelines[0], timelines[1]))
        or Fraction(videos[0]["avg_frame_rate"]) != Fraction(videos[1]["avg_frame_rate"])
    ):
        raise ValueError("Decoded frame timelines do not align")
    return {
        "frames": len(timelines[0]),
        "reference": videos[0],
        "candidate": videos[1],
        "temporal_alignment": "checked",
        "display_fidelity": "unverified",
    }


def launch_review(
    directory: Path, trial_id: str, viewer: str = "video-compare", bits: int = 8
) -> dict[str, Any]:
    pair = inspect_review(directory, trial_id)
    alignment = decoded_alignment(pair)
    executable = shutil.which(viewer)
    if not executable:
        raise ValueError("video-compare unavailable; open report.html for browser review instead")
    if bits not in (8, 10):
        raise ValueError("Display bits must be 8 or 10")
    command = [
        executable,
        "--no-auto-options-file",
        "--no-auto-filters",
        "-T",
        "off",
        "-d",
        "-v",
        "-a",
        "on",
    ]
    if bits == 10:
        command.append("-b")
    command.extend([pair["reference"]["path"], pair["candidate"]["path"]])
    # File-backed diagnostics cannot deadlock a long-lived viewer on a full pipe.
    with (directory / "native-review.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, shell=False, stdout=log, stderr=log)
    try:
        code = process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        code = None
    if code not in (None, 0):
        raise RuntimeError(
            f"Native viewer failed ({code}); see native-review.log. Browser report remains available."
        )
    return {
        **pair,
        "alignment": alignment,
        "pid": process.pid,
        "display_bits": bits,
        "launch_status": "started" if code is None else "exited",
        "visual_acceptance": "unreviewed",
    }


def record_review(
    directory: Path,
    trial_id: str,
    decision: str,
    reviewer: str,
    objections: list[float],
    note: str,
    method: str,
) -> dict[str, Any]:
    pair = inspect_review(directory, trial_id)
    if (
        decision not in ("accept", "reject")
        or not reviewer.strip()
        or method not in ("native", "browser", "editor")
    ):
        raise ValueError("Review needs accept/reject, reviewer and native/browser/editor method")
    if any(
        type(value) not in (int, float)
        or not math.isfinite(value)
        or not 0 <= value < pair["interval"]["seconds"]
        for value in objections
    ):
        raise ValueError("Objection timestamps must be finite seconds within the reviewed interval")
    path = directory / "visual-reviews.json"
    previous = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    record = {
        **pair,
        "decision": decision,
        "reviewer": reviewer.strip(),
        "objections": objections,
        "note": note,
        "method": method,
        "time": datetime.now(timezone.utc).isoformat(),
        "status": "current",
    }
    save(path, [item for item in previous if item["trial"] != trial_id] + [record])
    return record


def saved_reviews(directory: Path) -> list[dict[str, Any]]:
    path = directory / "visual-reviews.json"
    records = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    for record in records:
        try:
            current = inspect_review(directory, record["trial"])
            record["status"] = (
                "current"
                if all(
                    record.get(key) == current[key]
                    for key in (
                        "benchmark_identity",
                        "interval",
                        "reference",
                        "candidate",
                        "source_id",
                    )
                )
                else "invalid"
            )
        except (ValueError, OSError, KeyError, StopIteration):
            record["status"] = "invalid"
    return records
