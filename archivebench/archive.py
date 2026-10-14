"""Optional archival starting point: encode first, review, then separately clean up."""

import json
import os
from fractions import Fraction
from pathlib import Path
from typing import Any

from .core import (
    color_args,
    digest,
    fingerprint,
    inspect_source,
    primary,
    probe,
    run,
    save,
    validate_output,
)
from .encoders import SPECS, options
from .formats import output_video, retention, scale_filter, validate_formats

EXTENSIONS = {".mov", ".mp4", ".mkv", ".mxf", ".avi", ".mts", ".m2ts", ".webm", ".m4v"}


def safe(path: Path, root: Path | None = None) -> Path:
    path = path.absolute()
    for parent in (path, *path.parents):
        if parent.is_symlink() or getattr(os.path, "isjunction", lambda value: False)(parent):
            raise ValueError(f"Linked paths are unsupported: {parent}")
    full = path.resolve()
    if root is not None and (full == root.resolve() or not full.is_relative_to(root.resolve())):
        raise ValueError("Path outside selected root")
    return full


def candidates(root: Path) -> list[Path]:
    found = []
    for folder, directories, files in os.walk(root, followlinks=False):
        directories[:] = [
            name
            for name in sorted(directories)
            if "".join(c for c in name.lower() if c.isalnum())
            not in ("proxy", "proxies", "archivedfootage", "archives", "git", "node_modules")
            and not Path(folder, name).is_symlink()
            and not (Path(folder, name) / "archive-manifest.json").exists()
            and not (Path(folder, name) / "results.json").exists()
        ]
        for name in sorted(files):
            path = Path(folder, name)
            if (
                path.suffix.lower() in EXTENSIONS
                and ".archive." not in name.lower()
                and ".partial." not in name.lower()
                and not path.is_symlink()
            ):
                try:
                    found.append(safe(path, root))
                except ValueError:
                    continue
    return found


def validate_settings(settings: dict[str, Any]) -> None:
    if settings.get("version") not in (1, 2) or settings.get("type") != "archive-settings":
        raise ValueError("Export archive settings from a benchmark report")
    if settings.get("encoder") not in SPECS:
        raise ValueError("Unsupported archive format")
    validate_formats(settings)
    options(
        settings["encoder"],
        int(settings["quality"]),
        "yuv420p" if settings["pixel_format"] == "source" else settings["pixel_format"],
    )
    if not 0.1 <= float(settings.get("minimum_saving", 0.1)) < 1:
        raise ValueError("Minimum saving must be at least 10%")


def retained_audio(info: dict[str, Any], policy: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        s
        for i, s in enumerate((s for s in info["streams"] if s["codec_type"] == "audio"), 1)
        if policy["audio_mode"] != "none" and i not in policy["drop_audio_tracks"]
    ]


def verify_retention(
    original: dict[str, Any],
    encoded: dict[str, Any],
    source: Path,
    output: Path,
    policy: dict[str, Any],
    ffmpeg: str,
) -> None:
    def tags(src: dict[str, Any], dst: dict[str, Any]) -> None:
        # Muxers regenerate duration/encoder and bitrate statistics, not user metadata.
        ignored = {"encoder", "duration", "bps", "number_of_frames", "number_of_bytes"}
        actual = {k.lower(): v for k, v in dst.get("tags", {}).items()}
        for key, value in src.get("tags", {}).items():
            if key.lower() in ignored or key.lower().startswith("_statistics_"):
                continue
            if actual.get(key.lower()) != value:
                raise ValueError(f"Archive metadata mismatch: {key}")

    def payload(path: Path, index: int) -> str:
        return run(
            [
                ffmpeg,
                "-v",
                "error",
                "-nostdin",
                "-i",
                str(path),
                "-map",
                f"0:{index}",
                "-c",
                "copy",
                "-f",
                "hash",
                "-hash",
                "sha256",
                "-",
            ],
            86400,
        ).strip()

    for kind in ("audio", "subtitle", "attachment"):
        source_streams = [s for s in original["streams"] if s["codec_type"] == kind]
        if kind == "audio":
            source_streams = retained_audio(original, policy)
        elif policy[kind + "s"] == "drop":
            source_streams = []
        outputs = [s for s in encoded["streams"] if s["codec_type"] == kind]
        if len(outputs) != len(source_streams):
            raise ValueError(f"Archive {kind} selection mismatch")
        for src, dst in zip(source_streams, outputs):
            copied = kind != "audio" or policy["audio_mode"] == "copy"
            codec = src.get("codec_name") if copied else "aac"
            if dst.get("codec_name") != codec:
                raise ValueError(f"Archive {kind} codec mismatch")
            if any(
                bool(dst.get("disposition", {}).get(k)) != bool(v)
                for k, v in src.get("disposition", {}).items()
            ):
                raise ValueError(f"Archive {kind} disposition mismatch")
            if kind == "audio" and any(
                dst.get(k) != src.get(k) for k in ("channels", "sample_rate")
            ):
                raise ValueError("Archive audio channel/sample-rate mismatch")
            if copied:
                if kind == "attachment":
                    if not src.get("extradata_hash") or src["extradata_hash"] != dst.get(
                        "extradata_hash"
                    ):
                        raise ValueError("Archive attachment content mismatch")
                elif payload(source, src["index"]) != payload(output, dst["index"]):
                    raise ValueError(f"Archive copied {kind} content mismatch")
            if policy["metadata"] == "copy":
                tags(src, dst)
    if policy["metadata"] == "copy":
        tags(original["format"], encoded["format"])
        tags(primary(original), primary(encoded))
        chapters, outputs = original.get("chapters", []), encoded.get("chapters", [])
        if len(chapters) != len(outputs):
            raise ValueError("Archive chapter count mismatch")
        for src, dst in zip(chapters, outputs):
            if any(abs(float(src[k]) - float(dst[k])) > 0.002 for k in ("start_time", "end_time")):
                raise ValueError("Archive chapter timing mismatch")
            tags(src, dst)


def verify_archive(
    output: Path, source: Path, settings: dict[str, Any], ffmpeg: str, ffprobe: str
) -> None:
    original = probe(source, ffprobe)
    video = primary(original)
    video["fps"] = video["avg_frame_rate"]
    target = output_video(video, settings)
    validate_output(output, target, settings["encoder"], target["pix_fmt"], ffprobe)
    encoded = probe(output, ffprobe)
    if abs(float(original["format"]["duration"]) - float(encoded["format"]["duration"])) > 0.5:
        raise ValueError("Archive duration mismatch")
    policy = retention(settings)
    # Existing v1 jobs predate metadata checks; preserve their cleanup contract.
    if settings["version"] == 1:
        policy = {**policy, "metadata": "drop"}
    verify_retention(original, encoded, source, output, policy, ffmpeg)

    def count(path: Path) -> int:
        return int(
            run(
                [
                    ffprobe,
                    "-v",
                    "error",
                    "-count_frames",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=nb_read_frames",
                    "-of",
                    "default=nw=1:nk=1",
                    str(path),
                ],
                86400,
            ).strip()
        )

    if count(output) != count(source):
        raise ValueError("Archive frame count mismatch")
    run(
        [
            ffmpeg,
            "-v",
            "error",
            "-xerror",
            "-nostdin",
            "-i",
            str(output),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-f",
            "null",
            os.devnull,
        ],
        86400,
    )


def archive(
    source_root: Path,
    output_root: Path,
    settings_path: Path,
    execute: bool,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> None:
    source_root, output_root = safe(source_root), safe(output_root)
    if (
        not source_root.is_dir()
        or source_root == output_root
        or source_root.is_relative_to(output_root)
    ):
        raise ValueError("Choose distinct source/output folders; output cannot contain source")
    from .presets import resolve_settings

    settings = resolve_settings(json.loads(settings_path.read_text(encoding="utf-8")))
    validate_settings(settings)
    files = [path for path in candidates(source_root) if not path.is_relative_to(output_root)]
    print(
        f"Review list: {len(files)} files. Encoder: {settings['encoder']}; originals remain intact."
    )
    policy = retention(settings)
    print(
        json.dumps(
            {
                "pixel_format": settings["pixel_format"],
                "resolution": settings.get("resolution", "original"),
                "container": "MKV",
                **policy,
            }
        )
    )
    for path in files:
        print(path.relative_to(source_root))
    if not execute:
        print("Add --execute after reviewing this list to encode.")
        return
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "archive-manifest.json"
    manifest: dict[str, Any] = (
        json.loads(manifest_path.read_text())
        if manifest_path.exists()
        else {
            "version": 1,
            "source_root": str(source_root),
            "output_root": str(output_root),
            "settings": settings,
            "records": [],
        }
    )
    if (
        manifest["source_root"] != str(source_root)
        or manifest["output_root"] != str(output_root)
        or fingerprint(manifest["settings"]) != fingerprint(settings)
    ):
        raise ValueError(
            "Existing archive belongs to another source/settings; choose another output"
        )
    lock = output_root / ".lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        for path in files:
            output = safe(
                output_root / (str(path.relative_to(source_root)) + ".archive.mkv"), output_root
            )
            record = next((r for r in manifest["records"] if r["source"] == str(path)), None)
            original_hash = digest(path)
            if record:
                if original_hash != record["source_hash"]:
                    raise ValueError("Original changed since saved job")
                if record["status"] in ("verified", "not_worth_encoding"):
                    if record["status"] == "verified" and (
                        not output.exists() or digest(output) != record["output_hash"]
                    ):
                        raise ValueError("Verified archive changed/missing")
                    print(f"Skip completed: {path.name}")
                    continue
            elif output.exists():
                raise ValueError("Output exists without a manifest record; refusing overwrite")
            if not record:
                record = {
                    "source": str(path),
                    "output": str(output),
                    "source_hash": original_hash,
                    "status": "pending",
                    "output_hash": "",
                    "saving": 0.0,
                }
                manifest["records"].append(record)
                save(manifest_path, manifest)
            info = probe(path, ffprobe)
            video = inspect_source(path, 0, min(1, float(info["format"]["duration"])), ffprobe)
            target = output_video(video, settings)
            if any(
                s["codec_type"] not in ("video", "audio", "subtitle", "attachment")
                or s.get("disposition", {}).get("attached_pic")
                for s in info["streams"]
            ):
                raise ValueError(
                    "Data/unknown streams or cover art need a tested preservation path; refusing to omit them"
                )
            output.parent.mkdir(parents=True, exist_ok=True)
            if not output.exists():
                temporary = safe(output.with_name(output.name + ".partial.mkv"), output_root)
                args = [
                    ffmpeg,
                    "-hide_banner",
                    "-nostdin",
                    "-v",
                    "warning",
                    "-y",
                    "-i",
                    str(path),
                    "-map",
                    f"0:{video['index']}",
                ]
                retained = retained_audio(info, policy)
                for stream in retained:
                    args += ["-map", f"0:{stream['index']}"]
                for kind, spec in (("subtitles", "s"), ("attachments", "t")):
                    if policy[kind] == "copy":
                        args += ["-map", f"0:{spec}?", f"-c:{spec}", "copy"]
                if policy["metadata"] == "drop":
                    for spec in ("v", "a", "s"):
                        args += [f"-map_metadata:s:{spec}", "-1"]
                mapped = [video, *retained]
                for kind in ("subtitle", "attachment"):
                    if policy[kind + "s"] == "copy":
                        mapped += [s for s in info["streams"] if s["codec_type"] == kind]
                for i, stream in enumerate(mapped):
                    flags = "+".join(k for k, v in stream.get("disposition", {}).items() if v)
                    args += [f"-disposition:{i}", flags or "0"]
                args += [
                    "-map_metadata",
                    "0" if policy["metadata"] == "copy" else "-1",
                    "-map_chapters",
                    "0" if policy["metadata"] == "copy" else "-1",
                    "-fps_mode",
                    "passthrough",
                    *options(
                        settings["encoder"],
                        settings["quality"],
                        target["pix_fmt"],
                        scale_filter(video, target),
                    ),
                    "-g",
                    str(round(float(Fraction(video["fps"])) * 8)),
                    *color_args(video),
                    "-c:a",
                    "aac" if policy["audio_mode"] == "aac" else "copy",
                ]
                if policy["audio_mode"] == "aac":
                    for i, stream in enumerate(retained):
                        args += [
                            f"-b:a:{i}",
                            f"{stream['channels'] * policy['audio_kbps_per_channel']}k",
                        ]
                args += ["-f", "matroska", str(temporary)]
                print(f"Encoding: {path.name}", flush=True)
                run(args, 86400)
                verify_archive(temporary, path, settings, ffmpeg, ffprobe)
                temporary.replace(output)
            else:
                verify_archive(output, path, settings, ffmpeg, ffprobe)
            if digest(path) != original_hash:
                raise ValueError("Source changed during encoding")
            record["saving"] = 1 - output.stat().st_size / path.stat().st_size
            record["output_hash"] = digest(output)
            record["status"] = "verified"
            if record["saving"] < settings.get("minimum_saving", 0.1):
                output.unlink()
                record["status"] = "not_worth_encoding"
                record["output_hash"] = ""
            save(manifest_path, manifest)
            print(f"{record['status']}: {record['saving']:.1%} saved")
    finally:
        lock.unlink(missing_ok=True)


def cleanup(
    output_root: Path,
    execute: bool,
    reviewed: bool,
    ffmpeg: str = "ffmpeg",
    ffprobe: str = "ffprobe",
) -> None:
    output_root = safe(output_root)
    path = safe(output_root / "archive-manifest.json", output_root)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_settings(manifest["settings"])
    if manifest["version"] != 1 or manifest["output_root"] != str(output_root):
        raise ValueError("Invalid cleanup manifest")
    source_root = safe(Path(manifest["source_root"]))
    if source_root == output_root or source_root.is_relative_to(output_root):
        raise ValueError("Invalid cleanup source root")
    records = [record for record in manifest["records"] if record["status"] == "verified"]
    print(f"Cleanup review: {len(records)} verified originals. Deletion is permanent.")
    for record in records:
        print(record["source"])
    if not execute:
        print("After visual review, add --execute --reviewed to delete these originals.")
        return
    if not reviewed:
        raise ValueError("Explicit --reviewed is required after inspecting the archive clips")
    lock = output_root / ".lock"
    with lock.open("x") as stream:
        stream.write(str(os.getpid()))
    try:
        # Validate the whole selection before deleting any original.
        for record in records:
            source = safe(Path(record["source"]), source_root)
            output = safe(Path(record["output"]), output_root)
            expected = output_root / (str(source.relative_to(source_root)) + ".archive.mkv")
            if (
                output != expected
                or digest(source) != record["source_hash"]
                or digest(output) != record["output_hash"]
            ):
                raise ValueError("Source/output changed or path mismatch; cleanup refused")
            if 1 - output.stat().st_size / source.stat().st_size < manifest["settings"].get(
                "minimum_saving", 0.1
            ):
                raise ValueError("Insufficient actual savings")
            verify_archive(output, source, manifest["settings"], ffmpeg, ffprobe)
        for record in records:
            source = safe(Path(record["source"]), source_root)
            output = safe(Path(record["output"]), output_root)
            if digest(source) != record["source_hash"] or digest(output) != record["output_hash"]:
                raise ValueError("Files changed during cleanup checks")
            source.unlink()
            record["status"] = "original_deleted"
            save(path, manifest)
    finally:
        lock.unlink(missing_ok=True)
