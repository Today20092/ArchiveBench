"""Offline archive-job summary derived from the canonical manifest."""

import json
from collections import Counter
from html import escape
from pathlib import Path


def job_outcome(manifest: dict) -> str:
    records = {row["source"]: row for row in manifest.get("records", [])}
    counts = Counter(row.get("status") for row in records.values())
    selection = manifest.get("selected_sources")
    if selection is None and "selected_files" in manifest.get("job", {}):
        selection = [
            str(Path(manifest["source_root"]) / p) for p in manifest["job"]["selected_files"]
        ]
    finished = {"verified", "original_deleted", "keep_original", "not_worth_encoding", "failed"}
    unfinished = sum(
        records.get(source, {}).get("status") not in finished
        for source in set(selection or []) | records.keys()
    )
    next_step = (
        "Next: inspect the checkpoint and recover the selected file list before treating this job as complete."
        if selection is None
        else "Next: resolve failed files and resume the saved job for unfinished work. Completed files "
        "are rechecked; unfinished files restart from the beginning."
        if unfinished or counts["failed"]
        else "Next: inspect replacement acceptance for the verified outputs. Technical verification "
        "does not establish visual quality or editor compatibility."
        if counts["verified"]
        else "Next: keep the originals for files without a verified replacement; review their recorded reasons before changing settings."
        if counts["keep_original"] or counts["not_worth_encoding"]
        else "Next: review the recorded outputs and cleanup history."
    )
    return (
        f"Recorded outcome — Verified: {counts['verified']}; failed: {counts['failed']}; "
        f"unfinished: {unfinished if selection is not None else 'unknown (selection not recorded)'}. "
        + next_step
        + " Saved evidence is not a fresh check of changed files. Replacement acceptance and "
        "approval of an exact deletion preview are separate decisions; this summary authorizes neither."
    )


def refresh_summary(output_root: Path) -> None:
    # A full drive must not hide the original failure or prevent lock release.
    try:
        write_summary(output_root)
    except Exception as error:
        print(
            f"Archive summary could not be refreshed; use the checkpoint manifest: {error}",
            flush=True,
        )


def write_summary(output_root: Path) -> Path:
    from .archive import safe

    root = safe(output_root)
    manifest = json.loads(safe(root / "archive-manifest.json", root).read_text(encoding="utf-8"))
    records = {row["source"]: row for row in manifest.get("records", [])}
    selection = manifest.get("selected_sources")
    if selection is None and "selected_files" in manifest.get("job", {}):
        selection = [
            str(Path(manifest["source_root"]) / p) for p in manifest["job"]["selected_files"]
        ]
    sources = list(dict.fromkeys([*(selection or []), *records]))
    unfinished = 0
    reduction = deletion = reclaimed = 0
    unknown_sizes = 0
    rows = []
    labels = {
        "verified": "Verified; original retained",
        "original_deleted": "Original deleted",
        "keep_original": "Original retained",
        "not_worth_encoding": "Original retained—insufficient savings",
        "failed": "Failed; original retained",
    }
    for source in sources:
        record = records.get(source, {})
        status = record.get("status", "pending")
        if status not in labels:
            unfinished += 1
        if status in ("verified", "original_deleted"):
            src, dst = record.get("source_bytes"), record.get("output_bytes")
            if isinstance(src, int) and isinstance(dst, int) and src >= 0 and dst >= 0:
                reduction += src - dst
                if status == "verified":
                    deletion += src
                else:
                    reclaimed += src - dst
            else:
                unknown_sizes += 1
        detail = (
            record.get("error", "") if status == "failed" else "; ".join(record.get("gaps", []))
        )
        rows.append(
            "<tr>"
            + "".join(
                f"<td>{escape(str(value))}</td>"
                for value in (
                    source,
                    labels.get(status, "Unfinished"),
                    record.get("output", ""),
                    detail,
                )
            )
            + "</tr>"
        )
    job_path = manifest.get("job_path")
    links = '<a href="archive-manifest.json">Checkpoint manifest</a>'
    if job_path:
        path = Path(job_path).absolute()
        links += (
            f' · <a href="{escape(path.as_uri(), quote=True)}">Saved job: {escape(str(path))}</a>'
        )
        log = Path(str(path) + ".log")
        links += f' · <a href="{escape(log.as_uri(), quote=True)}">Job log (if created)</a>'
    resume = (
        f"Load the saved job {job_path} in the terminal UI and start/resume it."
        if job_path
        else "Use the saved manifest settings and original source/output paths to resume. No saved job location was recorded."
    )
    settings = {
        "settings": manifest.get("settings"),
        "preset": manifest.get("job", {}).get("preset"),
        "exceptions": manifest.get("job", {}).get("exceptions", []),
        "replacement_acceptance": manifest.get("replacement_acceptance", {}),
        "suitability_acceptance": manifest.get(
            "suitability_acceptance", {"status": "not-recorded"}
        ),
    }
    counts = Counter(record.get("status") for record in records.values())
    if not unfinished and not counts["failed"]:
        resume = (
            "Selection coverage is unknown; inspect the checkpoint before deciding what remains."
            if selection is None
            else "No unfinished or failed files are recorded. Follow the outcome-specific next step above."
        )
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Archive job summary</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}td,th{{padding:.6rem;border:1px solid #aaa;text-align:left;overflow-wrap:anywhere}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style>
<h1>Archive job summary</h1><p>Selected video files only; this is not a complete editing-project backup.</p>
<p>{escape(job_outcome(manifest))}</p>
<p>Source: {escape(str(manifest.get("source_root", "Not recorded")))} · Output: {escape(str(root))}</p>
<p>Last run: {escape(str(manifest.get("last_run", "Not recorded")))}</p>
<p>Recorded files: {len(records)} · Unfinished: {unfinished} · Failed: {sum(r.get("status") == "failed" for r in records.values())}</p>
<p>Verified: {counts["verified"]} · Kept original: {counts["keep_original"]} · Insufficient savings: {counts["not_worth_encoding"]} · Original deleted: {counts["original_deleted"]}</p>
<p>{"Selection coverage unknown; additional unfinished files may exist." if selection is None else "Selection coverage recorded."}</p>
<ul><li>Replacement size reduction: {reduction} bytes</li><li>Potential original deletion: {deletion} bytes</li><li>Net storage reclaimed after cleanup: {reclaimed} bytes</li></ul>
<p>Totals use recorded byte counts; {unknown_sizes} completed files have unknown sizes and are excluded. Insufficient-saving outputs are discarded and contribute no savings. Potential deletion is not approval or current eligibility; cleanup must recheck files and acceptance.</p>
<p>{links}</p><h2>Saved work and recovery</h2><p>{escape(resume)} If retrying, completed files are rechecked and unfinished files restart from their beginning. Resolve failed files before retrying. Original deletion is a separate approved action.</p>
<table><thead><tr><th>Source</th><th>Recorded outcome</th><th>Output</th><th>Details</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
<details><summary>Exact settings, preset scope and recorded acceptance</summary><pre>{escape(json.dumps(settings, indent=2))}</pre></details></html>"""
    destination = safe(root / "archive-summary.html", root)
    temporary = safe(root / "archive-summary.html.tmp", root)
    temporary.write_text(html, encoding="utf-8")
    temporary.replace(destination)
    return destination
