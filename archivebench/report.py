"""Offline report generation from canonical JSON; local paths stay out of shared reports."""

import csv
import json
import re
from pathlib import Path
from typing import Any

from .formats import format_variants
from .media import safe_asset_path


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(result))
    for trial in value["trials"] + value.get("screening", []):
        trial.pop("output", None)
        for field in ("review_media", "review_stills"):

            def sanitize_assets(item: Any) -> None:
                if isinstance(item, dict):
                    if "path" in item and not safe_asset_path(item["path"]):
                        item.pop("path")
                    for nested in item.values():
                        sanitize_assets(nested)
                elif isinstance(item, list):
                    for nested in item:
                        sanitize_assets(nested)

            sanitize_assets(trial.get(field))
    value["config"]["samples"] = [
        {**sample, "path": "[local source]"} for sample in value["config"]["samples"]
    ]
    if "validation_samples" in value["config"]:
        value["config"]["validation_samples"] = [
            {**sample, "path": "[local source]"} for sample in value["config"]["validation_samples"]
        ]
    for skipped in value["skipped"]:
        # FFmpeg diagnostics can contain local paths; raw errors remain in local results.json.
        skipped["reason"] = skipped["reason"].splitlines()[0][:160]
        for sample in result["config"]["samples"]:
            skipped["reason"] = skipped["reason"].replace(sample["path"], "[local source]")
        if re.search(r"[A-Za-z]:[\\/]|(?:^|[\s'\"\[])/", skipped["reason"]):
            skipped["reason"] = (
                "Local process failed. See local results.json for detailed diagnostics."
            )
    return value


def write_report(result: dict[str, Any], directory: Path) -> Path:
    assets = Path(__file__).parent / "assets"
    payload = json.dumps(public_result(result), ensure_ascii=True, allow_nan=False).replace(
        "<", "\\u003c"
    )
    template = (assets / "report.html").read_text(encoding="utf-8")
    script = (assets / "report.js").read_text(encoding="utf-8").replace("</script", "<\\/script")
    report = directory / "report.html"
    report.write_text(
        template.replace("__RESULTS__", payload).replace("__APP__", script), encoding="utf-8"
    )
    fields = [
        "id",
        "sample",
        "variant",
        "stage",
        "encoder",
        "quality",
        "pixel_format",
        "width",
        "height",
        "resolution",
        "vmaf",
        "vmaf_p5",
        "ssim",
        "bytes",
        "encode_seconds",
    ]
    with (directory / "trials.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(result["trials"])
    summary = [
        "# ArchiveBench results",
        "",
        f"Status: {result['status']}",
        f"Fresh-footage validation: {result.get('validation_status', 'provisional, no reviewed holdouts')}",
        "Format variants: "
        + "; ".join(
            f"{variant['label']} ({variant['pixel_format']}, {variant['resolution']})"
            for variant in format_variants(result["config"])
        ),
        "",
        "VMAF is a model score, not a percentage of original quality. Format comparisons include explicit transformations; review chroma and resolution tradeoffs separately.",
        "",
        "| Variant | Sample | Encoder | Quality control | VMAF | SSIM | MiB | Encode seconds |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in result["trials"]:
        summary.append(
            f"| {row.get('variant', 'legacy')} | {row['sample']} | {row['encoder']} | {row['quality']} | {row['vmaf']:.2f} | {row['ssim']:.4f} | {row['bytes'] / 1024**2:.2f} | {row['encode_seconds']:.2f} |"
        )
    summary.extend(
        [
            "",
            "Measured encoding excludes scoring, previews, hashes and archive verification.",
            "Duration projections are linear estimates from short samples; audio is excluded.",
            "Original 4:2:2 chroma is normalized for scoring a 4:2:0 output; VMAF does not quantify lost chroma detail.",
            "Reduced-resolution outputs are upscaled to the original dimensions for scoring; references are not downscaled.",
            f"Skipped/failed configurations: {len(result['skipped'])}.",
        ]
    )
    (directory / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return report
