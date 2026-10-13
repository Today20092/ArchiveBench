"""Optional companion previews. Review failures never change metric evidence."""

import hashlib
import json
import re
import subprocess
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from typing import Any


def safe_asset_path(value: Any) -> bool:
    return isinstance(value, str) and bool(
        re.fullmatch(r"review/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+\.(?:mp4|mkv|png)", value)
    )


def generate_review_media(
    result: dict[str, Any], directory: Path, remaining: Callable[[], float]
) -> None:
    from .core import fingerprint, run

    root = directory.resolve()
    ffmpeg = result["config"].get("ffmpeg", "ffmpeg")
    ffprobe = result["config"].get("ffprobe", "ffprobe")

    def check_budget() -> float:
        seconds = remaining()
        if seconds <= 0.1:
            raise TimeoutError("Review budget exhausted")
        return seconds

    def hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            while block := stream.read(1024 * 1024):
                check_budget()
                digest.update(block)
        return digest.hexdigest()

    def bounded(path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError("Review file outside run")
        return resolved

    def preview(source: Path, destination: Path, video: dict[str, Any]) -> dict[str, Any]:
        temporary = destination.with_name(destination.stem + "-partial.mp4")
        try:
            run(
                [
                    ffmpeg,
                    "-v",
                    "error",
                    "-nostdin",
                    "-y",
                    "-i",
                    str(source),
                    "-map",
                    "0:v:0",
                    "-an",
                    "-vf",
                    f"scale=trunc(iw/2)*2:trunc(ih/2)*2,setpts=N/({video['fps']}*TB)",
                    "-frames:v",
                    str(video["frames"]),
                    "-r",
                    video["fps"],
                    "-fps_mode",
                    "cfr",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-crf",
                    "18",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(temporary),
                ],
                check_budget(),
            )
            info = json.loads(
                run(
                    [
                        ffprobe,
                        "-v",
                        "error",
                        "-count_frames",
                        "-show_streams",
                        "-of",
                        "json",
                        str(temporary),
                    ],
                    check_budget(),
                )
            )["streams"][0]
            fps = Fraction(video["fps"])
            if (
                int(info["nb_read_frames"]) != video["frames"]
                or Fraction(info["avg_frame_rate"]) != fps
                or abs(float(info["duration"]) - video["frames"] / float(fps)) > 1 / float(fps)
            ):
                raise ValueError("Preview timeline mismatch")
            sha = hash_file(temporary)
            temporary.replace(destination)
            return {
                "path": destination.relative_to(root).as_posix(),
                "sha256": sha,
                "width": info["width"],
                "height": info["height"],
                "fps": video["fps"],
                "frames": video["frames"],
                "converted": True,
                "codec": "H.264",
                "pixel_format": "yuv420p",
                "bit_depth": 8,
                "audio": False,
                "crf": 18,
            }
        finally:
            temporary.unlink(missing_ok=True)

    for trial in result["trials"]:
        if not any(
            candidate.get("evidence_status") == "validated"
            and all(candidate[key] == trial.get(key) for key in ("variant", "encoder", "quality"))
            for candidate in result.get("validation_shortlist", [])
        ):
            continue
        sample = next(s for s in result["samples"] if s["id"] == trial["sample"])
        cached = trial.get("review_media")
        assets: dict[str, Any] = {
            "status": "unavailable",
            "note": "Review assets unavailable. Metric validation remains unchanged.",
        }
        trial["review_media"] = assets
        try:
            check_budget()
            source = bounded(Path(trial["output"]))
            if hash_file(source) != trial["sha256"]:
                raise ValueError("Measured clip changed")
            reference = bounded(root / sample["id"] / "reference.mkv")
            identity = json.loads(reference.with_name("reference.json").read_text())
            if hash_file(reference) != identity["sha256"]:
                raise ValueError("Reference changed")
            if cached and cached.get("status") == "available":
                for kind in ("original", "encoded", "exact"):
                    asset = cached[kind]
                    if (
                        not safe_asset_path(asset["path"])
                        or hash_file(bounded(root / asset["path"])) != asset["sha256"]
                    ):
                        raise ValueError("Cached review asset changed")
                trial["review_media"] = cached
                continue
            folder = bounded(
                root
                / "review"
                / fingerprint({"trial": trial["id"], "sha256": trial["sha256"]})[:20]
            )
            folder.mkdir(parents=True, exist_ok=True)
            exact = bounded(folder / "exact.mkv")
            temporary = bounded(folder / "exact-partial.mkv")
            try:
                with source.open("rb") as incoming, temporary.open("wb") as outgoing:
                    while block := incoming.read(1024 * 1024):
                        check_budget()
                        outgoing.write(block)
                if hash_file(temporary) != trial["sha256"]:
                    raise ValueError("Copy mismatch")
                temporary.replace(exact)
            finally:
                temporary.unlink(missing_ok=True)
            assets["exact"] = {
                "path": exact.relative_to(root).as_posix(),
                "sha256": trial["sha256"],
            }
            assets["original"] = preview(
                reference, bounded(folder / "original.mp4"), sample["video"]
            )
            assets["encoded"] = preview(source, bounded(folder / "encoded.mp4"), sample["video"])
            assets.update(
                status="available",
                note="Converted browser previews. Exact measured clip is available separately.",
            )
        except (OSError, ValueError, RuntimeError, KeyError, subprocess.TimeoutExpired):
            pass
