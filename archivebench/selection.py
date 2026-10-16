"""Shared archive source selection and immutable job construction."""

import copy
import os
from pathlib import Path

from .archive import candidates, safe
from .jobs import create_job, resume_destination, validate_job
from .presets import make_preset, resolve_settings


def selection_defaults(paths: list[Path]) -> tuple[Path, Path, list[tuple[Path, bool]]]:
    """Keep one stable relative-path namespace for the shared job engine."""
    paths = sorted({safe(p) for p in paths}, key=lambda p: str(p).casefold())
    if not paths or any(not p.exists() for p in paths):
        raise ValueError("Select existing folders or video files")
    if len(paths) == 1 and paths[0].is_dir():
        output, rows = project_defaults(paths[0])
        return paths[0], output, rows
    try:
        root = Path(os.path.commonpath([str(p if p.is_dir() else p.parent) for p in paths]))
    except ValueError as error:
        raise ValueError("Use a separate archive job for each source drive") from error
    files = set()
    for path in paths:
        if path.is_dir():
            files.update(candidates(path))
        elif path in candidates(path.parent):
            files.add(path)
        else:
            raise ValueError(f"Unsupported or excluded video: {path}")
    return root, root / "Archived Footage", [(p, True) for p in sorted(files)]


def project_defaults(root: Path) -> tuple[Path, list[tuple[Path, bool]]]:
    root = safe(root)
    files = candidates(root)
    original = [
        p
        for p in files
        if any(
            "".join(c for c in part.lower() if c.isalnum()) == "originalfootage"
            for part in p.relative_to(root).parts[:-1]
        )
    ]
    base = (
        root.parent
        if "".join(c for c in root.name.lower() if c.isalnum()) == "originalfootage"
        else root
    )
    return base / "Archived Footage", [(p, not original or p in original) for p in files]


def selected_job(
    source: Path, output: Path, preset: Path, selected: list[str], policies: dict
) -> dict:
    job = create_job(source, output, preset)
    settings = resolve_settings(job["preset"])
    settings.update(policies)
    document = make_preset(settings, job["preset"]["name"], job["preset"]["description"])
    document["scope"] = copy.deepcopy(job["preset"]["scope"])
    document["evidence"]["estimates"] = copy.deepcopy(job["preset"]["evidence"]["estimates"])
    document["evidence"]["packaging_status"] = (
        "Job-specific container/retention policy; compatibility preflight required"
    )
    job.update(
        preset=document, selected_files=sorted(set(selected)), continue_on_error=True, progress=True
    )
    validate_job(job)
    available = {p.relative_to(source.resolve()).as_posix() for p in candidates(source.resolve())}
    if not set(selected).issubset(available):
        raise ValueError("Selection contains missing or excluded files")
    return resume_destination(job)
