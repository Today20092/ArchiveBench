"""Offline manufacturer limits intersected with the existing hardware discovery."""

import os
import re
import subprocess
from collections.abc import Callable
from typing import Any

from .encoders import SPECS
from .driver_query import query_drivers, driver_verdict

MATRIX = "https://developer.nvidia.com/video-encode-decode-support-matrix"
SDK = "https://docs.nvidia.com/video-technologies/video-codec-sdk/13.0/nvenc-application-note/index.html"
REVISION = "2026-10-17"
AMD_MATRIX = (
    "https://github.com/GPUOpen-LibrariesAndSDKs/AMF/wiki/GPU-and-APU-HW-Features-and-Support"
)
APPLE_SPECS = [
    f"https://support.apple.com/en-us/{page}" for page in ("111894", "111869", "117736", "121555")
]

# Exact reviewed models only: an unfamiliar product must stay unknown, not inherit a limit.
RTX_MODELS = {
    "Turing": "2060|2060 Super|2070|2070 Super|2080|2080 Super|2080 Ti",
    "Ampere": "2050|3050|3050 Ti|3060|3060 Ti|3070|3070 Ti|3080|3080 Ti|3090|3090 Ti",
    "Ada": "4050|4060|4060 Ti|4070|4070 Super|4070 Ti|4070 Ti Super|4080|4080 Super|4090",
    "Blackwell": "5050|5060|5060 Ti|5070|5070 Ti|5080|5090",
}
LAYOUTS = {
    "yuv420p": {"yuv420p", "nv12"},
    "yuv420p10le": {"yuv420p10le", "p010le"},
    "yuv422p": {"yuv422p", "nv16"},
    "yuv422p10le": {"yuv422p10le", "p210le"},
}


def nvidia_generation(name: str) -> str | None:
    name = re.sub(r"\s+", " ", name.strip()).casefold()
    name = re.sub(r"^(?:nvidia )?geforce rtx ", "", name)
    name = re.sub(r" (?:laptop gpu|laptop)$", "", name)
    for generation, models in RTX_MODELS.items():
        if name in models.casefold().split("|"):
            return generation
    return None


def manufacturer_support(name: str, codec: str, pixel: str) -> bool | None:
    generation = nvidia_generation(name)
    if generation is None or pixel not in LAYOUTS:
        return None
    if codec == "av1":
        return generation in ("Ada", "Blackwell") and pixel.startswith("yuv420")
    if codec not in ("h264", "hevc"):
        return None
    if "422" in pixel and generation != "Blackwell":
        return False
    if codec == "h264" and "10" in pixel and generation != "Blackwell":
        return False
    return True


def amd_support(name: str, codec: str, pixel: str) -> bool | None:
    # RX family ranges are explicitly listed in AMD's VCN table; don't infer from Ryzen names.
    match = re.fullmatch(r"(?:AMD )?Radeon RX (\d{4})(?: ?(?:XT|XTX|GRE|M|S))?", name.strip(), re.I)
    if not match or pixel not in LAYOUTS or codec not in ("h264", "hevc", "av1"):
        return None
    model = match[1]
    if model[:2] in ("63", "64", "65"):
        return False  # Navi24 has no encoder, despite the RDNA 2 name.
    if model[:2] in ("53", "55", "56", "57", "66", "67", "68", "69"):
        av1 = False
    elif model[:2] in ("75", "76", "77", "78", "79") or model[:3] in ("906", "907"):
        av1 = True
    else:
        return None
    return (
        "422" not in pixel and not (codec == "h264" and "10" in pixel) and (codec != "av1" or av1)
    )


def add_limits(hardware: dict[str, Any], run: Callable[..., str]) -> dict[str, Any]:
    """Enrich the existing bounded inventory without running encodes or using the network."""
    drivers = query_drivers(hardware, run)
    formats = {}
    for encoder in hardware["configured"]:
        try:
            text = run(
                [hardware["tools"]["ffmpeg"]["path"], "-hide_banner", "-h", f"encoder={encoder}"], 5
            )
            match = re.search(r"Supported pixel formats:\s*([^\r\n]+)", text)
            formats[encoder] = match[1].split() if match else None
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            formats[encoder] = None
    return {
        **hardware,
        "driver_queries": drivers,
        "encoder_pixel_formats": formats,
        "manufacturer_sources": [MATRIX, SDK, AMD_MATRIX, *APPLE_SPECS],
        "table_revision": REVISION,
        "visibility": {
            key: os.environ[key]
            for key in ("CUDA_VISIBLE_DEVICES", "NVIDIA_VISIBLE_DEVICES")
            if key in os.environ
        },
    }


def check_capability(snapshot: dict[str, Any], encoder: str, pixel: str) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "encoder": encoder,
        "pixel_format": pixel,
        "status": "unknown",
        "reason": "Device capabilities unknown; actual encode probe required",
        "table_revision": snapshot.get("table_revision", REVISION),
        "source": "unknown",
    }
    native = driver_verdict(snapshot, encoder, pixel)
    if native:
        evidence.update(native)
        evidence["driver_evidence"] = native
    if "configured" in snapshot and encoder not in snapshot["configured"]:
        return {
            **evidence,
            "status": "unsupported",
            "source": "ffmpeg",
            "reason": "Not present in FFmpeg build",
        }
    formats = snapshot.get("encoder_pixel_formats", {}).get(encoder)
    # Hardware surfaces alone don't describe a layout; keep them probeable.
    if formats and set(formats).difference({"cuda", "qsv", "vaapi", "d3d11", "vulkan"}):
        if pixel in LAYOUTS and not LAYOUTS[pixel].intersection(formats):
            return {
                **evidence,
                "status": "unsupported",
                "source": "ffmpeg",
                "reason": f"Installed FFmpeg {encoder} cannot preserve requested bit depth/chroma ({pixel})",
            }
    if native:
        return evidence
    evidence["source"] = "manufacturer-fallback"
    if encoder.endswith("_nvenc"):
        devices = [
            device for device in snapshot.get("devices", []) if device.get("vendor") == "NVIDIA"
        ]
        if not devices:
            devices = [
                device
                for device in snapshot.get("devices", [])
                if re.search(r"NVIDIA|GeForce", device.get("name", ""), re.I)
            ]
        support = [manufacturer_support(gpu["name"], SPECS[encoder][0], pixel) for gpu in devices]
        evidence["devices"] = [
            {**gpu, "manufacturer_support": supported} for gpu, supported in zip(devices, support)
        ]
        evidence["manufacturer_sources"] = [MATRIX, SDK]
        if snapshot.get("visibility"):
            evidence["reason"] = "GPU visibility override; device mapping unknown, probe required"
        elif any(
            "NVIDIA inventory unavailable" in error
            for error in snapshot.get("inventory_errors", [])
        ):
            evidence["reason"] = "NVIDIA inventory incomplete; actual encode probe required"
        elif support and all(value is False for value in support):
            evidence.update(
                status="unsupported",
                reason=f"Manufacturer specifications exclude {encoder} {pixel} on "
                + ", ".join(gpu["name"] for gpu in devices),
            )
        elif len(support) == 1 and support[0] is True:
            evidence.update(
                status="candidate", reason="Hardware permits this format; probe required"
            )
        elif len(support) > 1:
            evidence["reason"] = "Multiple GPUs; actual FFmpeg device selection needs a probe"
    elif encoder.endswith("_amf"):
        adapters = snapshot.get("devices", [])
        names = (
            [
                row.get("name", "")
                for row in adapters
                if isinstance(row, dict) and re.search(r"AMD|Radeon", row.get("name", ""), re.I)
            ]
            if isinstance(adapters, list)
            else []
        )
        support = [amd_support(name, SPECS[encoder][0], pixel) for name in names]
        evidence["devices"] = [
            {"name": name, "manufacturer_support": supported}
            for name, supported in zip(names, support)
        ]
        evidence["manufacturer_sources"] = [AMD_MATRIX]
        if any(
            "Display inventory unavailable" in error
            for error in snapshot.get("inventory_errors", [])
        ):
            evidence["reason"] = "AMD adapter inventory incomplete; actual encode probe required"
        elif support and all(value is False for value in support):
            evidence.update(
                status="unsupported",
                reason=f"AMD specifications exclude {encoder} {pixel} on " + ", ".join(names),
            )
        elif len(support) == 1 and support[0] is True:
            evidence.update(
                status="candidate", reason="AMD hardware permits this format; probe required"
            )
    elif encoder.endswith("_videotoolbox"):
        chip = snapshot.get("apple_chip") or ""
        evidence["manufacturer_sources"] = APPLE_SPECS
        if re.fullmatch(r"Apple M[1-4](?: (?:Pro|Max|Ultra))?", chip):
            evidence["device"] = chip
            evidence["codec_support"] = True
            evidence["reason"] = (
                "Apple documents H.264/HEVC hardware encoding; chroma/bit-depth support needs a probe"
            )
    elif not any(encoder.endswith("_" + kind) for kind in ("qsv", "amf", "vaapi", "videotoolbox")):
        evidence.update(status="candidate", reason="CPU encoder listed; actual encode required")
    return evidence


def require_capability(snapshot: dict[str, Any], encoder: str, pixel: str) -> dict[str, Any]:
    evidence = check_capability(snapshot, encoder, pixel)
    if evidence["status"] == "unsupported":
        raise ValueError(evidence["reason"])
    return evidence
