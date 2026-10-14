"""Offline report generation from canonical JSON; local paths stay out of shared reports."""

import csv
import json
import re
from html import escape
from pathlib import Path
from typing import Any

from .formats import format_variants
from .media import safe_asset_path
from .validation import quality_targets
from .presets import encoder_options
from .encoders import SPECS


def public_result(result: dict[str, Any]) -> dict[str, Any]:
    value = json.loads(json.dumps(result))
    for trial in value["trials"] + value.get("screening", []):
        trial.pop("output", None)
        if trial.get("encoder") in SPECS and "pixel_format" in trial:
            trial["preset_codec"] = SPECS[trial["encoder"]][0]
            variant = next(
                (
                    item
                    for item in value["config"].get("variants", [])
                    if item["id"] == trial.get("variant")
                ),
                value["config"],
            )
            trial["preset_encoder_options"] = encoder_options(
                {**trial, "pixel_format": variant.get("pixel_format", trial["pixel_format"])}
            )
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
    from .review import saved_reviews

    assets = Path(__file__).parent / "assets"
    reviews = saved_reviews(directory)
    public = public_result(result)
    public["visual_reviews"] = [
        {
            **{
                key: record.get(key)
                for key in (
                    "benchmark_identity",
                    "trial",
                    "source_id",
                    "interval",
                    "decision",
                    "method",
                    "time",
                    "status",
                    "objections",
                )
            },
            "candidate_sha256": record.get("candidate", {}).get("sha256"),
            "reference_sha256": record.get("reference", {}).get("sha256"),
        }
        for record in reviews
    ]
    payload = json.dumps(public, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    template = (assets / "report.html").read_text(encoding="utf-8")
    decisions = (
        '<section class="section" aria-label="Saved visual decisions"><h2>Saved visual decisions</h2><p>User attestations, separate from metric validation. Invalid decisions cannot support replacement.</p><ul>'
        + "".join(
            "<li>"
            + escape(
                f"{record['trial']}: {record['decision']} ({record['status']}, {record['method']}) by {record['reviewer']}; objection seconds {record['objections']}. {record['note']}"
            )
            + "</li>"
            for record in reviews
        )
        + "</ul></section>"
        if reviews
        else ""
    )
    template = template.replace("<footer>", decisions + "<footer>")
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
        f"Quality targets: {quality_targets(result['config'])}",
        f"Measured encodes per setting: {result['config'].get('encode_repeats', 1)}",
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
    if result.get("validation_shortlist"):
        summary.extend(["", "## Fresh checks by target", ""])
        for candidate in result["validation_shortlist"]:
            summary.append(
                f"- {candidate['variant']} / {candidate['encoder']} q{candidate['quality']}: "
                f"{candidate.get('target_statuses', candidate.get('evidence_status', 'incomplete'))}"
            )
    (directory / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return report
