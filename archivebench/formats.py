"""Shared, validated output choices for benchmarks and archive jobs."""

from fractions import Fraction
from typing import Any

PIXEL_FORMATS = ("source", "yuv420p", "yuv420p10le", "yuv422p", "yuv422p10le")
RESOLUTIONS = {
    "original": None,
    "2160p": (3840, 2160),
    "1440p": (2560, 1440),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
}


def retention(settings: dict[str, Any]) -> dict[str, Any]:
    # Version 1 archive manifests retain their original policy for restart and cleanup.
    legacy = settings.get("type") == "archive-settings" and settings.get("version") == 1
    return {
        "audio_mode": settings.get("audio_mode", "aac" if legacy else "copy"),
        "drop_audio_tracks": settings.get("drop_audio_tracks", [3, 4] if legacy else []),
        "audio_kbps_per_channel": settings.get("audio_kbps_per_channel", 192),
        "subtitles": settings.get("subtitles", "drop" if legacy else "copy"),
        "attachments": settings.get("attachments", "drop" if legacy else "copy"),
        "metadata": settings.get("metadata", "copy"),
    }


def validate_formats(settings: dict[str, Any]) -> None:
    if settings.get("pixel_format") not in PIXEL_FORMATS:
        raise ValueError("Choose source, 8/10-bit 4:2:0, or 8/10-bit 4:2:2")
    resolution = settings.get("resolution", "original")
    if not isinstance(resolution, str) or resolution not in RESOLUTIONS:
        raise ValueError("Choose original, 2160p, 1440p, 1080p or 720p resolution")
    policy = retention(settings)
    if policy["audio_mode"] not in ("copy", "aac", "none"):
        raise ValueError("Audio mode must be copy, aac or none")
    tracks = policy["drop_audio_tracks"]
    if not isinstance(tracks, list) or any(type(t) is not int or t < 1 for t in tracks):
        raise ValueError("Dropped audio tracks must be positive, one-based track numbers")
    if len(tracks) != len(set(tracks)):
        raise ValueError("Dropped audio tracks must not repeat")
    if (
        type(policy["audio_kbps_per_channel"]) is not int
        or not 32 <= policy["audio_kbps_per_channel"] <= 512
    ):
        raise ValueError("AAC bitrate must be 32..512 kbps per channel")
    for key in ("subtitles", "attachments", "metadata"):
        if policy[key] not in ("copy", "drop"):
            raise ValueError(f"{key} must be copy or drop")


def output_video(video: dict[str, Any], settings: dict[str, Any]) -> dict[str, Any]:
    pixel = settings["pixel_format"]
    if pixel == "source":
        pixel = video["pix_fmt"]
        if pixel not in PIXEL_FORMATS[1:]:
            raise ValueError(
                f"Source pixel format {pixel} is unsupported; select an explicit output format"
            )
    width, height = video["width"], video["height"]
    bounds = RESOLUTIONS[settings.get("resolution", "original")]
    if bounds:
        if height > width:
            bounds = bounds[::-1]
        factor = min(Fraction(1), Fraction(bounds[0], width), Fraction(bounds[1], height))
        if factor < 1:
            width, height = (
                max(2, int(width * factor) // 2 * 2),
                max(2, int(height * factor) // 2 * 2),
            )
    if width % 2 or (pixel.startswith("yuv420") and height % 2):
        raise ValueError("Source dimensions are incompatible with the selected chroma format")
    return {**video, "width": width, "height": height, "pix_fmt": pixel}


def scale_filter(video: dict[str, Any], output: dict[str, Any]) -> str:
    if (video["width"], video["height"]) == (output["width"], output["height"]):
        return ""
    return f"scale={output['width']}:{output['height']}:flags=lanczos"
