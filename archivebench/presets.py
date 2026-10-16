"""Portable settings and historical evidence; project paths belong to jobs."""

import json
from pathlib import Path
from typing import Any

from .encoders import SPECS, options


def starter_paths() -> list[Path]:
    """Bundled, portable starting settings; no benchmark evidence is implied."""
    return sorted(Path(__file__).with_name("starter_presets").glob("*.json"))


def settings_fingerprint(settings: dict[str, Any]) -> str:
    """Canonical settings binding, portable to the offline JavaScript exporter."""

    def normalize(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, list):
            return [normalize(item) for item in value]
        return int(value) if isinstance(value, float) and value.is_integer() else value

    return json.dumps(
        normalize(settings), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )


def encoder_options(settings: dict[str, Any]) -> list[str]:
    if type(settings.get("quality")) is not int:
        raise ValueError("Preset quality must be an integer")
    return options(
        settings["encoder"],
        settings["quality"],
        "yuv420p" if settings["pixel_format"] == "source" else settings["pixel_format"],
    )


def make_preset(settings: dict[str, Any], name: str = "", description: str = "") -> dict[str, Any]:
    from .archive import validate_settings

    controls = encoder_options(settings)
    validate_settings(settings)
    encoder = settings["encoder"]
    hardware = "CPU" if encoder.startswith("lib") else encoder.rsplit("_", 1)[-1].upper()
    return {
        "version": 1,
        "type": "archive-preset",
        "name": name or f"{SPECS[encoder][0].upper()} / {encoder} ({hardware})",
        "description": description
        or "Compare measured size, time and footage before choosing; this preset does not guarantee quality on untested footage.",
        "settings": dict(settings),
        "encoder_options": controls,
        "scope": {"environment": {}, "footage": []},
        "evidence": {
            "settings_fingerprint": settings_fingerprint(settings),
            "benchmark_identity": settings.get("benchmark_identity"),
            "measurement_status": settings.get("evidence_status", "unknown"),
            "visual_status": "unreviewed",
            "estimates": {
                "basis": "unknown",
                "coverage": [],
                "exclusions": ["retained streams", "verification", "untested footage"],
            },
        },
    }


def resolve_settings(document: dict[str, Any]) -> dict[str, Any]:
    from .archive import validate_settings

    if not isinstance(document, dict):
        raise ValueError("Settings must be a JSON object")
    if document.get("type") != "archive-preset":
        validate_settings(document)
        return dict(document)
    if document.get("version") != 1:
        raise ValueError("Unsupported archive-preset version")
    if not all(isinstance(document.get(key), dict) for key in ("settings", "scope", "evidence")):
        raise ValueError("Preset settings, scope and evidence must be objects")
    if not all(
        isinstance(document.get(key), str) and document[key].strip()
        for key in ("name", "description")
    ):
        raise ValueError("Preset name and description are required")
    settings = document["settings"]
    validate_settings(settings)
    if document.get("encoder_options") != encoder_options(settings):
        raise ValueError("Preset encoder options do not match supported settings")
    if document["evidence"].get("settings_fingerprint") != settings_fingerprint(settings):
        raise ValueError("Preset settings changed; historical evidence is invalid")
    if not isinstance(document["scope"].get("environment"), dict) or not isinstance(
        document["scope"].get("footage"), list
    ):
        raise ValueError("Preset scope requires environment and footage")
    return dict(settings)


def inspect_preset(
    document: dict[str, Any], context: dict[str, Any] | None = None
) -> dict[str, Any]:
    settings = resolve_settings(document)
    preset = document if document.get("type") == "archive-preset" else make_preset(settings)
    context = context or {}
    encoders = context.get("supported_encoders")
    formats = context.get("supported_pixel_formats")
    unsupported = []
    if encoders is not None and settings["encoder"] not in encoders:
        unsupported.append("encoder/hardware unavailable")
    footage = context.get("footage", [])
    required_formats = (
        [item.get("pix_fmt", item.get("pixel_format")) for item in footage]
        if settings["pixel_format"] == "source"
        else [settings["pixel_format"]]
    )
    if formats is not None and any(fmt and fmt not in formats for fmt in required_formats):
        unsupported.append("output pixel format unavailable")
    tested = preset["scope"]["footage"]
    return {
        "preset": preset,
        "compatibility": "unsupported" if unsupported else "not-probed",
        "unsupported": unsupported,
        "footage_scope": "matches historical scope"
        if footage
        and all(
            any(
                scope and all(item.get(key) == value for key, value in scope.items())
                for scope in tested
            )
            for item in footage
        )
        else "untested",
        "sample_check": "skipped by user" if context.get("skip_sample_check") else "recommended",
        "current_project_validated": False,
    }
