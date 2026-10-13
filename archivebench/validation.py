"""Reviewed holdout sections and fixed candidate qualification."""

import math
from pathlib import Path
from typing import Any


def validation_sections(
    samples: list[dict[str, Any]],
    durations: dict[str, float],
    reviewed: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    sources = list(dict.fromkeys(str(Path(s["path"]).resolve()) for s in samples))
    sections = []
    for source in sources:
        tuning = [s for s in samples if str(Path(s["path"]).resolve()) == source]
        matches = (
            []
            if reviewed is None
            else [s for s in reviewed if str(Path(s["path"]).resolve()) == source]
        )
        if reviewed is not None:
            if len(matches) != 1:
                raise ValueError("Review exactly one validation section per source")
            section = {**matches[0], "path": source}
        else:
            length = min(60, 2 * max(float(s["seconds"]) for s in tuning))
            intervals = sorted(
                (float(s["start"]), float(s["start"]) + float(s["seconds"])) for s in tuning
            )
            gaps = []
            end = 0.0
            for start, stop in intervals:
                if start - end >= length:
                    gaps.append((end, start))
                end = max(end, stop)
            if durations[source] - end >= length:
                gaps.append((end, durations[source]))
            if not gaps:
                sections.append(
                    {"path": source, "unavailable": "Insufficient non-overlapping footage"}
                )
                continue
            section = {"path": source, "start": gaps[-1][1] - length, "seconds": length}
        start, length = float(section["start"]), float(section["seconds"])
        if (
            not math.isfinite(start)
            or not math.isfinite(length)
            or start < 0
            or not 0 < length <= 60
            or start + length > durations[source] + 0.01
        ):
            raise ValueError("Invalid validation interval")
        if any(
            start < float(s["start"]) + float(s["seconds"]) and start + length > float(s["start"])
            for s in tuning
        ):
            raise ValueError("Validation sections overlap tuning footage")
        sections.append(section)
    if reviewed is not None and len(reviewed) != len(sources):
        raise ValueError("Review exactly one validation section per source")
    return sections


def shortlist(result: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = {}
    for trial in result["trials"]:
        if trial.get("stage", "tuning") == "tuning":
            key = (trial.get("variant", "legacy"), trial["encoder"], trial["quality"])
            groups.setdefault(key, {})[trial["sample"]] = trial
    required = {f"sample-{i + 1}" for i in range(len(result["config"]["samples"]))}
    sources = {s["id"]: s for s in result["samples"] if s.get("stage", "tuning") == "tuning"}
    qualified = []
    for (variant, encoder, quality), rows in groups.items():
        if set(rows) != required or any(
            t["vmaf"] < result["config"]["target_vmaf"] for t in rows.values()
        ):
            continue
        rates: dict[str, list[tuple[float, float, float]]] = {}
        for sample_id, trial in rows.items():
            sample = sources[sample_id]
            rates.setdefault(sample.get("source_id", sample_id), []).append(
                (
                    trial["bytes"] / sample["seconds"],
                    trial["encode_seconds"] / sample["seconds"],
                    sample.get("source_seconds", sample["seconds"]),
                )
            )
        qualified.append(
            {
                "variant": variant,
                "encoder": encoder,
                "quality": quality,
                "projected_bytes": sum(
                    v[0][2] * sum(r[0] for r in v) / len(v) for v in rates.values()
                ),
                "projected_seconds": sum(
                    v[0][2] * sum(r[1] for r in v) / len(v) for v in rates.values()
                ),
            }
        )
    selected = []
    for variant in dict.fromkeys(c["variant"] for c in qualified):
        candidates = [c for c in qualified if c["variant"] == variant]
        for metric in ("projected_bytes", "projected_seconds"):
            candidate = min(candidates, key=lambda c: (c[metric], c["encoder"], c["quality"]))
            if candidate not in selected:
                selected.append(candidate)
    return selected
