"""Native-size display stills from matched decoded scored frames."""

import json
import math
import subprocess
import struct
from collections.abc import Callable
from fractions import Fraction
from pathlib import Path
from typing import Any


def generate_stills(
    result: dict[str, Any], directory: Path, remaining: Callable[[], float]
) -> None:
    from .core import digest, fingerprint, run

    finalists = {
        (c["variant"], c["encoder"], c["quality"])
        for c in result.get("validation_shortlist", [])
        if c.get("evidence_status") == "validated"
    }
    root = directory.resolve()
    for trial in result["trials"]:
        if (trial.get("variant"), trial["encoder"], trial["quality"]) not in finalists:
            continue
        sample = next(s for s in result["samples"] if s["id"] == trial["sample"])
        fps = Fraction(sample["video"]["fps"])
        # One second separates chosen measured moments; subsampled indices already name decoded frames.
        selected: list[dict[str, Any]] = []
        frames = [
            f
            for f in trial.get("vmaf_frames", [])
            if isinstance(f.get("frame_index"), int)
            and f["frame_index"] >= 0
            and math.isfinite(f["vmaf"])
        ]
        for frame in sorted(frames, key=lambda f: (f["vmaf"], f["frame_index"])):
            if all(
                abs(frame["frame_index"] - f["frame_index"]) / float(fps) >= 1 for f in selected
            ):
                selected.append(frame)
                if len(selected) == 3:
                    break
        old = trial.get("review_stills", {})
        evidence: dict[str, Any] = {
            "status": "complete",
            "spacing_seconds": 1,
            "moments": [],
            "note": "Native-size RGB PNG display conversions cannot certify source chroma or bit depth. Sharing the review folder reveals footage.",
        }
        if len(selected) < 3:
            evidence["note"] += (
                f" Only {len(selected)} separated scored moments are available; unscored frames are not invented."
            )
        reference = root / trial["sample"] / "reference.mkv"
        encoded = Path(trial["output"])
        asset_dir = root / "review" / fingerprint([trial["id"], trial["sha256"]])[:24]
        try:
            if remaining() <= 0.1:
                raise TimeoutError("Review budget exhausted")
            if not reference.resolve().is_relative_to(root) or not encoded.resolve().is_relative_to(
                root
            ):
                raise ValueError("Review inputs outside run")
            if (
                digest(reference)
                != json.loads(reference.with_suffix(".json").read_text())["sha256"]
                or digest(encoded) != trial["sha256"]
            ):
                raise ValueError("Review inputs changed")
            asset_dir.mkdir(parents=True, exist_ok=True)
            if not asset_dir.resolve().is_relative_to(root):
                raise ValueError("Review assets outside run")
            for frame in sorted(selected, key=lambda f: f["frame_index"]):
                index = frame["frame_index"]
                moment = {
                    "frame_index": index,
                    "seconds": float(Fraction(index) / fps),
                    "vmaf": frame["vmaf"],
                }
                for kind, source, width, height in [
                    ("original", reference, sample["video"]["width"], sample["video"]["height"]),
                    (
                        "encoded",
                        encoded,
                        trial.get("width", sample["video"]["width"]),
                        trial.get("height", sample["video"]["height"]),
                    ),
                ]:
                    path = asset_dir / f"frame-{index}-{kind}.png"
                    if not path.resolve().is_relative_to(root):
                        raise ValueError("Review asset outside run")
                    prior = next(
                        (
                            m.get(kind, {})
                            for m in old.get("moments", [])
                            if m["frame_index"] == index
                        ),
                        {},
                    )
                    if not (path.is_file() and digest(path) == prior.get("sha256")):
                        if remaining() <= 0.1:
                            raise TimeoutError("Review budget exhausted")
                        temporary = path.with_suffix(".partial.png")
                        if not temporary.resolve().is_relative_to(root):
                            raise ValueError("Review temporary outside run")
                        run(
                            [
                                result.get("config", {}).get("ffmpeg", "ffmpeg"),
                                "-v",
                                "error",
                                "-nostdin",
                                "-y",
                                "-i",
                                str(source),
                                "-vf",
                                f"select=eq(n\\,{index})",
                                "-frames:v",
                                "1",
                                "-fps_mode",
                                "passthrough",
                                str(temporary),
                            ],
                            remaining(),
                        )
                        with temporary.open("rb") as stream:
                            header = stream.read(24)
                        if header[:8] != b"\x89PNG\r\n\x1a\n" or struct.unpack(
                            ">II", header[16:24]
                        ) != (width, height):
                            raise ValueError("Still dimensions mismatch")
                        temporary.replace(path)
                    moment[kind] = {
                        "path": path.relative_to(root).as_posix(),
                        "sha256": digest(path),
                        "width": width,
                        "height": height,
                    }
                evidence["moments"].append(moment)
        except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.TimeoutExpired):
            evidence["status"] = "incomplete"
            evidence["note"] += (
                " Some stills could not be completed or verified. Restore run inputs or resume with more time. Metric validation is unchanged."
            )
        trial["review_stills"] = evidence
