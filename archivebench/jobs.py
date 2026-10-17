"""Local project jobs with portable preset snapshots and explicit file exceptions."""

import copy
import json
import math
import shutil
import subprocess
from collections.abc import Callable
from contextlib import contextmanager
from fractions import Fraction
from uuid import uuid4
from pathlib import Path
from typing import Any

from .archive import archive, candidates, safe
from .core import color_args, digest, fingerprint, inspect_source, probe, run, save, validate_output
from .encoders import options
from .formats import output_video, retention, scale_filter
from .presets import inspect_preset, make_preset, resolve_settings, starter_paths
from .mux import suffix, mux_args, stream_gaps
from .hardware import inventory, failure_status
from .hardware_limits import check_capability, require_capability


def discover_job(output: Path) -> dict[str, Any] | None:
    """Find the immutable job beside its outputs, preferring the execution checkpoint."""
    output = safe(output)
    manifest_path = output / "archive-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if "job" not in manifest:
            raise ValueError(
                "Destination contains a legacy archive; resume its original settings or choose another destination"
            )
        job = manifest["job"]
    elif (output / "archive-job.json").exists():
        job = json.loads((output / "archive-job.json").read_text(encoding="utf-8"))
    elif Path(str(output) + ".job.json").exists():
        job = json.loads(Path(str(output) + ".job.json").read_text(encoding="utf-8"))
    else:
        return None
    validate_job(job)
    if safe(Path(job["output_root"])) != output:
        raise ValueError(
            "Saved job destination differs; restore its original location or choose another destination"
        )
    return copy.deepcopy(job)


def resume_destination(job: dict[str, Any]) -> dict[str, Any]:
    """Reuse the destination snapshot only when selection and settings agree."""
    saved = discover_job(Path(job["output_root"]))
    if saved is None:
        return job

    def selection(value):
        source, output = Path(value["source_root"]), Path(value["output_root"])
        return set(
            value.get(
                "selected_files",
                [
                    p.relative_to(source).as_posix()
                    for p in candidates(source)
                    if not p.is_relative_to(output)
                ],
            )
        )

    deleted = set(completed_deletions(saved))
    if (
        saved["source_root"] != job["source_root"]
        or selection(saved) - deleted != selection(job) - deleted
    ):
        raise ValueError(
            "Destination job selection conflicts; resume the saved selection or choose another destination"
        )
    if (
        resolve_settings(saved["preset"]) != resolve_settings(job["preset"])
        or saved["exceptions"] != job["exceptions"]
    ):
        raise ValueError(
            "Destination job settings conflict; resume the saved settings or choose another destination"
        )
    return saved


def completed_deletions(job: dict[str, Any]) -> dict[str, dict]:
    """Missing originals are complete only when their checkpoint replacements still match."""
    source, output = safe(Path(job["source_root"])), safe(Path(job["output_root"]))
    path = safe(output / "archive-manifest.json", output)
    if not path.exists():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    records = [
        record for record in manifest.get("records", []) if record["status"] == "original_deleted"
    ]
    if not records:
        return {}
    if (
        manifest.get("version") != 1
        or manifest.get("source_root") != str(source)
        or manifest.get("output_root") != str(output)
        or manifest.get("job") != job
        or manifest.get("settings") != resolve_settings(job["preset"])
    ):
        raise ValueError(
            "Existing archive belongs to another source/settings; choose another output"
        )
    exceptions = {item["path"].casefold(): item for item in job["exceptions"]}
    missing = {
        safe(Path(value), source)
        for value in manifest.get(
            "selected_sources", [record["source"] for record in manifest["records"]]
        )
        if not Path(value).is_file()
    }
    if missing - {Path(record["source"]) for record in records}:
        raise ValueError("Selected file missing or excluded")
    completed = {}
    for record in records:
        original = safe(Path(record["source"]), source)
        relative = original.relative_to(source).as_posix()
        exception = exceptions.get(relative.casefold(), {})
        settings = resolve_settings(exception.get("preset", job["preset"]))
        replacement = safe(Path(record["output"]), output)
        if (
            relative in completed
            or original.exists()
            or ("selected_files" in job and relative not in job["selected_files"])
            or exception.get("action") == "keep-original"
            or record.get("settings") != settings
            or replacement != output / (relative + suffix(settings))
        ):
            raise ValueError("Deleted-original record mapping/settings do not match saved job")
        if not replacement.is_file() or digest(replacement) != record["output_hash"]:
            raise ValueError("Deleted-original replacement changed/missing")
        completed[relative] = record
    return completed


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
        if safe(scratch, parent) != scratch:
            raise ValueError("Preflight scratch path changed")
        shutil.rmtree(scratch)


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
    if "selected_files" in job:
        selected = job["selected_files"]
        if (
            not isinstance(selected, list)
            or not selected
            or any(not isinstance(p, str) for p in selected)
        ):
            raise ValueError("Select at least one relative file")
        paths = [relative_path(p).casefold() for p in selected]
        if len(set(paths)) != len(paths):
            raise ValueError("Duplicate selected file")
    for key in ("continue_on_error", "progress"):
        if key in job and type(job[key]) is not bool:
            raise ValueError(f"{key} must be boolean")
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
                    ("container", "mkv"),
                    ("data_mode", "reject"),
                    ("timecode_mode", "reject"),
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
    job: dict[str, Any],
    ffprobe: str = "ffprobe",
    ffmpeg: str = "ffmpeg",
    alternatives: list[Path] | None = None,
    *,
    hardware: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_job(job)
    if hardware is None:
        try:
            hardware = inventory(ffmpeg, ffprobe)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            hardware = {"status": "unknown", "reason": str(error)}
    source, output = safe(Path(job["source_root"])), safe(Path(job["output_root"]))
    if not source.is_dir() or source == output or source.is_relative_to(output):
        raise ValueError("Invalid job roots")
    exceptions = {
        relative_path(item["path"]).casefold(): item for item in job.get("exceptions", [])
    }
    rows, destinations, used = [], set(), set()
    deleted = completed_deletions(job)
    used.update(key for key in exceptions if key in {relative.casefold() for relative in deleted})
    available = candidates(source)
    if "selected_files" in job:
        chosen = {relative_path(p).casefold() for p in job["selected_files"]}
        if not chosen.issubset(
            {p.relative_to(source).as_posix().casefold() for p in available}
            | {relative.casefold() for relative in deleted}
        ):
            raise ValueError("Selected file missing or excluded")
        available = [p for p in available if p.relative_to(source).as_posix().casefold() in chosen]
    for path in available:
        if path.is_relative_to(output):
            continue
        relative = path.relative_to(source).as_posix()
        item = exceptions.get(relative.casefold(), {})
        if item:
            used.add(relative.casefold())
        settings = resolve_settings(item.get("preset", job["preset"]))
        destination = safe(output / (relative + suffix(settings)), output)
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

                gaps = preservation_gaps(path, info, settings)
                if gaps:
                    raise ValueError("; ".join(gaps))
                gaps = stream_gaps(info, settings)
                if gaps:
                    raise ValueError("; ".join(gaps))
                if (
                    sum(
                        stream["codec_type"] == "video"
                        and not stream.get("disposition", {}).get("attached_pic")
                        for stream in info["streams"]
                    )
                    != 1
                ):
                    raise ValueError("Multiple video streams require a tested preservation path")
                video = inspect_source(path, 0, min(1, float(info["format"]["duration"])), ffprobe)
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
                characteristics["fps"] = str(Fraction(video["avg_frame_rate"]))
                scope = inspect_preset(
                    item.get("preset", job["preset"]), {"footage": [characteristics]}
                )
                row.update(
                    footage=characteristics,
                    footage_scope=scope["footage_scope"],
                    sample_check=scope["sample_check"],
                )
                target = output_video(video, settings)
                row["capability"] = check_capability(
                    hardware, settings["encoder"], target["pix_fmt"]
                )
                require_capability(hardware, settings["encoder"], target["pix_fmt"])
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
                        *mux_args(settings, info),
                        str(Path(scratch) / ("probe." + settings.get("container", "mkv"))),
                    ]
                    run(args, 30)
                    validate_output(
                        Path(args[-1]), target, settings["encoder"], target["pix_fmt"], ffprobe
                    )
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
            except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                row.update(
                    action="keep-original",
                    output=None,
                    compatibility="unsupported"
                    if isinstance(error, ValueError)
                    else failure_status(str(error)),
                    gaps=[str(error)],
                )
        rows.append(row)
    if set(exceptions) != used:
        raise ValueError("Exception path does not match an eligible source file")
    ancestor = output
    while not ancestor.exists():
        ancestor = ancestor.parent
    result = {
        "files": rows,
        "hardware": hardware,
        "completed_deletions": list(deleted.values()),
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
    if alternatives is None:
        alternatives = starter_paths()
    if alternatives and any(row["gaps"] for row in rows):
        result["alternative_selection"] = (
            "Select an alternative explicitly and preflight the new job; current job remains unchanged"
        )
        result["alternatives"] = []
        result["preflight"]["maximum_alternative_probes_per_file"] = len(alternatives)
        for path in alternatives:
            candidate = copy.deepcopy(job)
            candidate["output_root"] = str(
                output.parent / f".archivebench-alternative-{uuid4().hex}"
            )
            candidate["selected_files"] = [row["relative"] for row in rows]
            candidate["exceptions"] = [
                item for item in job["exceptions"] if item["path"] not in deleted
            ]
            document = json.loads(path.read_text(encoding="utf-8"))
            candidate["preset"] = document
            item = {"path": str(path), "preset": document}
            try:
                checked = inspect_job(
                    candidate, ffprobe, ffmpeg, alternatives=[], hardware=hardware
                )
                item.update(
                    compatibility="short probes passed for all selected encodes"
                    if all(not row["gaps"] for row in checked["files"])
                    else "unsupported"
                    if any(row["compatibility"] == "unsupported" for row in checked["files"])
                    else "probe-failed",
                    files=checked["files"],
                    estimates=checked["estimates"],
                )
            except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                item.update(
                    compatibility="unsupported"
                    if isinstance(error, ValueError)
                    else failure_status(str(error)),
                    gaps=[str(error)],
                )
            result["alternatives"].append(item)
    return result


def suitability_decision(job: dict[str, Any], plan: dict[str, Any], accept: bool = False) -> dict:
    """Consent for this selection and settings; never a visual or cleanup attestation."""
    output = safe(Path(job["output_root"]))
    path = safe(output / "suitability-acceptance.json", output)
    scope = []
    for row in plan["files"]:
        if row["output"]:
            stat = Path(row["source"]).stat()
            scope.append(
                {
                    "source": row["source"],
                    "size": stat.st_size,
                    "modified_ns": stat.st_mtime_ns,
                    "footage": row.get("footage"),
                    "footage_scope": row.get("footage_scope"),
                    "settings": row["settings"],
                }
            )
    binding = fingerprint({"job": job, "scope": scope})
    required = any(row.get("footage_scope") != "matches historical scope" for row in scope)
    recorded = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    if not isinstance(recorded, dict):
        raise ValueError("Invalid suitability acceptance record")
    if not accept and recorded.get("status") == "accepted-uncertain":
        previous = recorded.get("scope", [])
        deleted = {item["source"] for item in plan.get("completed_deletions", [])}
        if (
            isinstance(previous, list)
            and all(
                isinstance(item, dict) and isinstance(item.get("source"), str) for item in previous
            )
            and recorded.get("binding") == fingerprint({"job": job, "scope": previous})
            and [item for item in previous if item["source"] not in deleted] == scope
        ):
            return recorded
    if accept and required:
        recorded = {
            "status": "accepted-uncertain",
            "binding": binding,
            "scope": scope,
            "note": "Explicit suitability acceptance; no visual review or deletion approval",
        }
        save(path, recorded)
    if required:
        return (
            recorded
            if recorded.get("binding") == binding and recorded.get("status") == "accepted-uncertain"
            else {"status": "acceptance-required", "binding": binding}
        )
    return {"status": "historical-scope-matches" if scope else "no-compatible-encodes"}


def run_job(
    job_path: Path,
    execute: bool = False,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
    stop_requested: Callable[[], bool] | None = None,
    accept_uncertain_suitability: bool = False,
) -> dict[str, Any]:
    job = json.loads(job_path.read_text(encoding="utf-8"))
    print(
        "Job preflight performs up to one frame per eligible file and, on incompatibility, up to four bundled alternative probes per file in temporary scratch (30-second limit per probe). This is compatibility checking; full archive encoding requires --execute.",
        flush=True,
    )
    plan = inspect_job(job, ffprobe, ffmpeg)
    if stop_requested and stop_requested():
        raise KeyboardInterrupt
    plan["suitability"] = suitability_decision(job, plan, accept_uncertain_suitability)
    encodes = sum(row["action"] == "encode" for row in plan["files"])
    print(
        f"Preflight: {encodes} files can be encoded; {len(plan['files']) - encodes} keep originals.\n"
        f"Saved job: {job_path}\nSource: {job['source_root']}\nOutput: {job['output_root']}\n"
        f"Space planning allowance: {plan['estimates']['scratch_bytes']} bytes "
        f"(source-size estimate, not guaranteed output size); available: {plan['estimates']['available_bytes']} bytes.\n"
        "Duration and output-size estimates, when available below, use historical video measurements; "
        "retained streams, verification and untested footage are excluded. Otherwise estimates are unknown.\n"
        "Stop retains completed records; current processing must finish stopping, and unfinished files "
        "restart from the beginning. Originals remain intact.\n"
        + (
            "Next: review incompatibility reasons; no files are ready to encode with these choices."
            if not encodes
            else "Next: review the plan and historical scope before starting. Compatibility is not quality acceptance."
        ),
        flush=True,
    )
    print(json.dumps(plan, indent=2))
    if execute:
        if plan["suitability"]["status"] == "acceptance-required":
            raise ValueError(
                "Accept uncertain preset suitability explicitly with --accept-uncertain-suitability after reviewing preflight"
            )
        archive(
            Path(job["source_root"]),
            Path(job["output_root"]),
            job_path,
            True,
            ffmpeg,
            ffprobe,
            job=job,
            plan=plan,
            stop_requested=stop_requested,
        )
    return plan
