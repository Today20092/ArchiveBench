"""Job replacement evidence: automated checks and explicit human decisions."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .archive import safe, verify_archive
from .core import digest, fingerprint, probe, save
from .presets import resolve_settings
from .formats import retention
from .mux import suffix


def preservation_gaps(
    source: Path, info: dict[str, Any], settings: dict[str, Any] | None = None
) -> list[str]:
    gaps = []
    tags = [
        info.get("format", {}).get("tags", {}),
        *(stream.get("tags", {}) for stream in info.get("streams", [])),
    ]
    if (
        any("timecode" in key.casefold() for group in tags for key in group)
        and (settings or {}).get("timecode_mode", "reject") == "reject"
    ):
        gaps.append("Timecode requires a tested preservation/relink path; keep original")
    sidecars = [
        path.name
        for path in source.parent.iterdir()
        if path.is_file()
        and path != source
        and path.suffix.casefold() in {".xmp", ".xml", ".bim", ".cpi", ".thm"}
        and (
            path.stem.casefold() == source.stem.casefold()
            or path.name.casefold().startswith(source.name.casefold() + ".")
        )
    ]
    if sidecars:
        gaps.append("Sidecar preservation is untested; keep original: " + ", ".join(sidecars))
    return gaps


def inspect_acceptance(
    output_root: Path, ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe"
) -> dict[str, Any]:
    from .jobs import validate_job

    root = safe(output_root)
    manifest = json.loads((root / "archive-manifest.json").read_text(encoding="utf-8"))
    if "job" not in manifest:
        raise ValueError(
            "Legacy manifest: use documented --reviewed cleanup; no acceptance migration"
        )
    job = manifest["job"]
    validate_job(job)
    source_root = safe(Path(job["source_root"]))
    if (
        manifest.get("version") != 1
        or manifest.get("output_root") != str(root)
        or manifest.get("source_root") != str(source_root)
        or job["output_root"] != str(root)
        or root == source_root
        or source_root.is_relative_to(root)
    ):
        raise ValueError("Invalid acceptance roots/manifest")
    base = resolve_settings(job["preset"])
    if manifest["settings"] != base:
        raise ValueError("Manifest settings differ from saved job")
    exceptions = {item["path"].casefold(): item for item in job["exceptions"]}
    mapping, seen, gaps = [], set(), []
    for record in manifest["records"]:
        if record["status"] != "verified":
            continue
        source = safe(Path(record["source"]), source_root)
        output = safe(Path(record["output"]), root)
        relative = source.relative_to(source_root).as_posix()
        if "selected_files" in job and relative not in job["selected_files"]:
            raise ValueError("Record is outside the saved file selection")
        exception = exceptions.get(relative.casefold(), {})
        settings = resolve_settings(exception.get("preset", job["preset"]))
        if exception.get("action") == "keep-original" or record.get("settings") != settings:
            raise ValueError("Record settings differ from saved job/exception")
        if relative.casefold() in seen or output != root / (relative + suffix(settings)):
            raise ValueError("Duplicate record or mapping mismatch")
        seen.add(relative.casefold())
        if digest(source) != record["source_hash"] or digest(output) != record["output_hash"]:
            raise ValueError("Source/output changed; acceptance invalid")
        if 1 - output.stat().st_size / source.stat().st_size < settings.get("minimum_saving", 0.1):
            raise ValueError("Insufficient actual savings")
        verify_archive(output, source, settings, ffmpeg, ffprobe)
        gaps.extend(preservation_gaps(source, probe(source, ffprobe), settings))
        mapping.append(
            {
                "source": str(source),
                "output": str(output),
                "source_hash": record["source_hash"],
                "output_hash": record["output_hash"],
                "settings": settings,
                "retained_requirements": retention(settings),
            }
        )
    binding = fingerprint({"job": job, "mapping": mapping})
    decisions = manifest.get("replacement_acceptance", {})

    def current_acceptance(kind):
        record = decisions.get(kind)
        return (
            isinstance(record, dict)
            and record.get("binding") == binding
            and record.get("decision") == "accept"
            and not record.get("unmet_requirements")
        )

    accepted = (
        all(current_acceptance(kind) for kind in ("visual", "editor"))
        or (
            current_acceptance("quality-tradeoff")
            and all(
                not isinstance(decisions.get(kind), dict)
                or decisions[kind].get("binding") != binding
                or decisions[kind].get("decision") != "reject"
                or decisions["quality-tradeoff"].get("recorded_at", "")
                > decisions[kind].get("recorded_at", "")
                for kind in ("visual", "editor")
            )
        )
    ) and not any(
        isinstance(record, dict)
        and record.get("binding") == binding
        and record.get("unmet_requirements")
        for record in decisions.values()
    )
    return {
        "binding": binding,
        "mapping": mapping,
        "gaps": gaps,
        "attestations": decisions,
        "eligible": mapping if accepted and not gaps else [],
        "caveat": "Quality-tradeoff acceptance does not claim visual/editor inspection. "
        "Unknown proprietary metadata and sidecar requirements must be reported as unmet.",
    }


def record_acceptance(
    output_root: Path,
    kind: str,
    decision: str,
    reviewer: str,
    *,
    editor: str = "",
    project_copy: str = "",
    note: str = "",
    unmet_requirements: list[str] | None = None,
) -> dict[str, Any]:
    if kind not in ("visual", "editor", "quality-tradeoff") or decision not in ("accept", "reject"):
        raise ValueError("Choose visual/editor/quality-tradeoff and accept/reject")
    if not reviewer.strip() or not note.strip():
        raise ValueError("Reviewer and decision note are required")
    if kind == "editor" and (not editor.strip() or not project_copy.strip()):
        raise ValueError("Named editor/version and separate project copy are required")
    unmet = unmet_requirements or []
    if not isinstance(unmet, list) or any(
        not isinstance(value, str) or not value.strip() for value in unmet
    ):
        raise ValueError("Unmet requirements must be a list of nonempty strings")
    root = safe(output_root)
    lock = root / ".lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        state = inspect_acceptance(root)
        if not state["mapping"]:
            raise ValueError("No verified outputs to review")
        if decision == "accept" and (state["gaps"] or unmet):
            raise ValueError("Unmet preservation requirements: keep originals")
        record = {
            "kind": kind,
            "decision": decision,
            "reviewer": reviewer,
            "note": note,
            "editor": editor,
            "project_copy": project_copy,
            "unmet_requirements": unmet,
            "binding": state["binding"],
            "mapping": state["mapping"],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        path = root / "archive-manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest.setdefault("replacement_acceptance", {})[kind] = record
        save(path, manifest)
        from .job_summary import refresh_summary

        refresh_summary(root)
        return record
    finally:
        lock.unlink(missing_ok=True)
