"""Explicit archive container and camera-stream policies, shared by preflight and execution."""

from typing import Any


def validate_mux(settings: dict[str, Any]) -> None:
    if settings.get("container", "mkv") not in ("mkv", "mov", "mp4"):
        raise ValueError("Container must be mkv, mov or mp4")
    if settings.get("data_mode", "reject") not in ("reject", "drop"):
        raise ValueError("Data policy must be reject or drop")
    if settings.get("timecode_mode", "reject") not in ("reject", "preserve", "drop"):
        raise ValueError("Timecode policy must be reject, preserve or drop")
    if settings.get("timecode_mode") == "preserve" and settings.get("container", "mkv") == "mkv":
        raise ValueError("Timecode preservation requires MOV or MP4")


def timecode(info: dict[str, Any]) -> str | None:
    values = {
        str(v)
        for item in [info.get("format", {}), *info.get("streams", [])]
        for k, v in item.get("tags", {}).items()
        if k.lower() == "timecode"
    }
    if len(values) > 1:
        raise ValueError("Conflicting source timecodes")
    return next(iter(values), None)


def stream_gaps(info: dict[str, Any], settings: dict[str, Any]) -> list[str]:
    gaps = []
    tc = timecode(info)
    mode = settings.get("timecode_mode", "reject")
    if tc and mode == "reject":
        gaps.append("Timecode requires an explicit preservation or drop policy")
    for stream in info["streams"]:
        kind = stream["codec_type"]
        if (
            kind == "data"
            and stream.get("codec_tag_string") == "tmcd"
            and tc
            and mode in ("preserve", "drop")
        ):
            continue
        if (
            kind not in ("video", "audio", "subtitle", "attachment")
            or stream.get("disposition", {}).get("attached_pic")
        ) and settings.get("data_mode", "reject") != "drop":
            gaps.append("Data/unknown streams or cover art require an explicit drop policy")
    return gaps


def suffix(settings: dict[str, Any]) -> str:
    return ".archive." + settings.get("container", "mkv")


def mux_args(settings: dict[str, Any], info: dict[str, Any]) -> list[str]:
    container = settings.get("container", "mkv")
    args = []
    if container != "mkv":
        args += ["-movflags", "+faststart"]
        if settings["encoder"].startswith("hevc") or settings["encoder"] == "libx265":
            args += ["-tag:v", "hvc1"]
        if settings.get("timecode_mode") == "preserve" and timecode(info):
            args += ["-timecode", str(timecode(info))]
        else:
            args += ["-write_tmcd", "0"]
    return args + ["-f", "matroska" if container == "mkv" else container]
