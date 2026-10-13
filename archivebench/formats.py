"""Shared, validated output choices for benchmarks and archive jobs."""

from fractions import Fraction
import re
from typing import Any

PIXEL_FORMATS = ("source", "yuv420p", "yuv420p10le", "yuv422p", "yuv422p10le")
RESOLUTIONS = {
    "original": None,
    "2160p": (3840, 2160),
    "1440p": (2560, 1440),
    "1080p": (1920, 1080),
    "720p": (1280, 720),
}

VARIANT_PRESETS = [
    {
        "id": "match-source",
        "label": "Match source",
        "pixel_format": "source",
        "resolution": "original",
    },
    {
        "id": "420-10-original",
        "label": "10-bit 4:2:0 original",
        "pixel_format": "yuv420p10le",
        "resolution": "original",
    },
    {
        "id": "420-10-1080p",
        "label": "10-bit 4:2:0 capped 1080p",
        "pixel_format": "yuv420p10le",
        "resolution": "1080p",
    },
    {
        "id": "420-8-1080p",
        "label": "8-bit 4:2:0 capped 1080p",
        "pixel_format": "yuv420p",
        "resolution": "1080p",
    },
]


def format_variants(config: dict[str, Any]) -> list[dict[str, Any]]:
    if "variants" not in config:
        return [
            {
                "id": "legacy",
                "label": "Single format",
                "pixel_format": config.get("pixel_format"),
                "resolution": config.get("resolution", "original"),
            }
        ]
    variants = config["variants"]
    if not isinstance(variants, list) or not variants:
        raise ValueError("Select at least one named format variant")
    ids = set()
    for variant in variants:
        if isinstance(variant, dict) and set(variant) - {
            "id",
            "label",
            "pixel_format",
            "resolution",
        }:
            raise ValueError(
                "Variants contain only id, label, pixel_format and resolution; retention is experiment-wide"
            )
        if (
            not isinstance(variant, dict)
            or not isinstance(variant.get("id"), str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", variant["id"])
        ):
            raise ValueError("Variant id must be a short lowercase name with digits or hyphens")
        if variant["id"] in ids:
            raise ValueError("Variant ids must be unique")
        if re.fullmatch(r"con|prn|aux|nul|com[1-9]|lpt[1-9]", variant["id"]):
            raise ValueError("Variant id cannot be a reserved Windows filename")
        ids.add(variant["id"])
        if not isinstance(variant.get("label"), str) or not variant["label"].strip():
            raise ValueError("Give each variant a label")
        validate_formats({**config, **variant})
    return variants


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
