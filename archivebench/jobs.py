"""Local project jobs with portable preset snapshots and explicit file exceptions."""

import copy
import json
import math
import shutil
from contextlib import contextmanager
from uuid import uuid4
from pathlib import Path
from typing import Any

from .archive import archive, candidates, safe
from .core import color_args, primary, probe, run
from .encoders import options
from .formats import output_video, retention, scale_filter
from .presets import inspect_preset, make_preset, resolve_settings


@contextmanager
def preflight_scratch(output: Path):
    parent = output
    while not parent.exists():
        parent = parent.parent
    scratch = safe(parent / f".archivebench-preflight-{uuid4().hex}", parent)
    # Inherit workspace permissions; tempfile's private ACL fails under Windows restricted tokens.
    scratch.mkdir()
    try:
        yield scratch
    finally:
        shutil.rmtree(safe(scratch, parent))


def relative_path(value: str) -> str:
    path = Path(value)
    if not value or path.is_absolute() or path.drive or ".." in path.parts or value == ".":
        raise ValueError("Exception paths must be relative files within the source root")
    return path.as_posix()


def validate_job(job: dict[str, Any]) -> None:
    if not isinstance(job, dict) or job.get("type") != "archive-job" or job.get("version") != 1:
        raise ValueError("Unsupported archive job")
    if (
        not all(
            isinstance(job.get(key), str) and job[key] for key in ("source_root", "output_root")
        )
        or not isinstance(job.get("preset"), dict)
        or not isinstance(job.get("exceptions"), list)
    ):
        raise ValueError("Job roots, preset and exceptions are required")
    resolve_settings(job["preset"])
    seen = set()
    for item in job.get("exceptions", []):
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("path"), str)
            or not isinstance(item.get("action"), str)
        ):
            raise ValueError("Exceptions require a path and action")
        key = relative_path(item["path"])
        if key.casefold() in seen:
            raise ValueError("Duplicate exception path")
        seen.add(key.casefold())
        if item["action"] == "stronger-setting":
            if not isinstance(item.get("preset"), dict):
                raise ValueError("Stronger-setting exceptions require a preset snapshot")
            base, override = resolve_settings(job["preset"]), resolve_settings(item["preset"])
            if any(
                base.get(k, default) != override.get(k, default)
                for k, default in (
                    ("version", 2),
                    ("encoder", None),
                    ("pixel_format", None),
                    ("resolution", "original"),
                    ("minimum_saving", 0.1),
                )
            ) or retention(base) != retention(override):
                raise ValueError(
                    "Stronger-setting exceptions must keep the same encoder and policy"
                )
            inverse = base["encoder"].endswith("_videotoolbox")
            if (
                override["quality"] <= base["quality"]
                if inverse
                else override["quality"] >= base["quality"]
            ):
                raise ValueError("Exception must request a stronger quality setting")
        elif item["action"] != "keep-original":
            raise ValueError("Unknown exception action")


def create_job(
    source: Path, output: Path, preset: Path, exceptions: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    # Validate paths before reading external documents, including malformed exception paths.
    if exceptions is not None and not isinstance(exceptions, list):
        raise ValueError("Exceptions must be a list")
    for item in exceptions or []:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("path"), str)
            or item.get("action") not in ("keep-original", "stronger-setting")
        ):
            raise ValueError("Exceptions require a relative path and supported action")
        relative_path(item["path"])
    source, output = safe(source), safe(output)
    if not source.is_dir() or source == output or source.is_relative_to(output):
        raise ValueError("Choose distinct source/output folders; output cannot contain source")
    document = json.loads(preset.read_text(encoding="utf-8"))
    snapshot = (
        document
        if document.get("type") == "archive-preset"
        else make_preset(resolve_settings(document))
    )
    resolved = []
    for item in exceptions or []:
        entry = {"path": relative_path(item["path"]), "action": item["action"]}
        if entry["action"] == "stronger-setting":
            if not isinstance(item.get("preset"), (str, dict)):
                raise ValueError("Stronger-setting exceptions require a preset")
            value = item["preset"]
            override = (
                json.loads(Path(value).read_text(encoding="utf-8"))
                if isinstance(value, str)
                else value
            )
            entry["preset"] = (
                override
                if override.get("type") == "archive-preset"
                else make_preset(resolve_settings(override))
            )
        resolved.append(entry)
    job = {
        "version": 1,
        "type": "archive-job",
        "source_root": str(source),
        "output_root": str(output),
        "preset": copy.deepcopy(snapshot),
        "exceptions": resolved,
    }
    validate_job(job)
    return job


def inspect_job(
    job: dict[str, Any], ffprobe: str = "ffprobe", ffmpeg: str = "ffmpeg"
) -> dict[str, Any]:
    validate_job(job)
    source, output = safe(Path(job["source_root"])), safe(Path(job["output_root"]))
    if not source.is_dir() or source == output or source.is_relative_to(output):
        raise ValueError("Invalid job roots")
    exceptions = {
        relative_path(item["path"]).casefold(): item for item in job.get("exceptions", [])
    }
    rows, destinations, used = [], set(), set()
    for path in candidates(source):
        if path.is_relative_to(output):
            continue
        relative = path.relative_to(source).as_posix()
        item = exceptions.get(relative.casefold(), {})
        if item:
            used.add(relative.casefold())
        settings = resolve_settings(item.get("preset", job["preset"]))
        destination = safe(output / (relative + ".archive.mkv"), output)
        if str(destination).casefold() in destinations:
            raise ValueError("Archive destination collision")
        destinations.add(str(destination).casefold())
        row: dict[str, Any] = {
            "source": str(path),
            "relative": relative,
            "action": item.get("action", "encode"),
            "output": str(destination),
            "settings": settings,
            "compatibility": "not-probed",
            "gaps": [],
            "estimates": {"status": "unknown"},
        }
        if row["action"] == "keep-original":
            row.update(output=None, settings=None, compatibility="not-required")
        else:
            try:
                info = probe(path, ffprobe)
                from .acceptance import preservation_gaps

                gaps = preservation_gaps(path, info)
                if gaps:
                    raise ValueError("; ".join(gaps))
                if any(
                    stream["codec_type"] not in ("video", "audio", "subtitle", "attachment")
                    or stream.get("disposition", {}).get("attached_pic")
                    for stream in info["streams"]
                ):
                    raise ValueError(
                        "Data/unknown streams or cover art require a tested preservation path"
                    )
                if sum(stream["codec_type"] == "video" for stream in info["streams"]) != 1:
                    raise ValueError("Multiple video streams require a tested preservation path")
                video = primary(info)
                characteristics = {
                    key: video[key]
                    for key in (
                        "width",
                        "height",
                        "pix_fmt",
                        "fps",
                        "color_space",
                        "color_transfer",
                        "color_primaries",
                    )
                    if key in video
                }
                characteristics["fps"] = video.get("avg_frame_rate", video.get("r_frame_rate"))
                scope = inspect_preset(
                    item.get("preset", job["preset"]), {"footage": [characteristics]}
                )
                row.update(
                    footage=characteristics,
                    footage_scope=scope["footage_scope"],
                    sample_check=scope["sample_check"],
                )
                target = output_video(video, settings)
                policy = retention(settings)
                with preflight_scratch(output) as scratch:
                    args = [ffmpeg, "-v", "error", "-nostdin", "-i", str(path), "-map", "0:v:0"]
                    audio = [
                        stream for stream in info["streams"] if stream["codec_type"] == "audio"
                    ]
                    for index, stream in enumerate(audio, 1):
                        if (
                            policy["audio_mode"] != "none"
                            and index not in policy["drop_audio_tracks"]
                        ):
                            args += ["-map", f"0:{stream['index']}"]
                    for kind, selector in (("subtitles", "s"), ("attachments", "t")):
                        if policy[kind] == "copy":
                            args += ["-map", f"0:{selector}?"]
                    args += [
                        "-c",
                        "copy",
                        *options(
                            settings["encoder"],
                            settings["quality"],
                            target["pix_fmt"],
                            scale_filter(video, target),
                        ),
                        *color_args(video),
                        "-c:a",
                        "aac" if policy["audio_mode"] == "aac" else "copy",
                        "-t",
                        "0.1",
                        "-frames:v",
                        "1",
                        "-f",
                        "matroska",
                        str(Path(scratch) / "probe.mkv"),
                    ]
                    run(args, 30)
                row["compatibility"] = (
                    "short encode/mux probe passed; full retention verification pending"
                )
                evidence = (
                    item.get("preset", job["preset"]).get("evidence", {}).get("estimates", {})
                )
                rates = (
                    evidence.get("video_bytes_per_second"),
                    evidence.get("encode_seconds_per_second"),
                )
                if evidence.get("basis") == "measured" and all(
                    isinstance(rate, (int, float))
                    and not isinstance(rate, bool)
                    and math.isfinite(rate)
                    and rate >= 0
                    for rate in rates
                ):
                    duration = float(info["format"]["duration"])
                    row["estimates"] = {
                        "status": "historical-video-only",
                        "video_bytes": duration * rates[0],
                        "encode_seconds": duration * rates[1],
                        "exclusions": ["retained streams", "verification", "untested footage"],
                        "coverage": evidence.get("coverage", []),
                    }
            except (ValueError, RuntimeError) as error:
                row.update(
                    action="keep-original",
                    output=None,
                    compatibility="unsupported",
                    gaps=[str(error)],
                )
        rows.append(row)
    if set(exceptions) != used:
        raise ValueError("Exception path does not match an eligible source file")
    ancestor = output
    while not ancestor.exists():
        ancestor = ancestor.parent
    return {
        "files": rows,
        "preflight": {
            "maximum_frames_per_file": 1,
            "timeout_seconds_per_probe": 30,
            "scratch": "job output ancestor, inherited permissions, removed after each probe",
        },
        "current_project_validated": False,
        "visual_status": "unreviewed",
        "estimates": {
            "status": "unknown"
            if any(row["estimates"]["status"] == "unknown" and row["output"] for row in rows)
            or not any(row["output"] for row in rows)
            else "historical-video-only",
            "scratch_bytes": sum(
                Path(row["source"]).stat().st_size for row in rows if row["output"]
            ),
            "available_bytes": shutil.disk_usage(ancestor).free,
            "scratch_basis": "source-size planning allowance; output size not guaranteed",
        },
    }


def run_job(
    job_path: Path, execute: bool = False, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"
) -> dict[str, Any]:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    print(
        "Job preflight performs up to one frame per eligible file in temporary scratch (30-second probe limit). This is compatibility checking; full archive encoding requires --execute.",
        flush=True,
    )
    plan = inspect_job(job, ffprobe, ffmpeg)
    print(json.dumps(plan, indent=2))
    if execute:
        archive(
            Path(job["source_root"]),
            Path(job["output_root"]),
            job_path,
            True,
            ffmpeg,
            ffprobe,
            job=job,
            plan=plan,
        )
    return plan
