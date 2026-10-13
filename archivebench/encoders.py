"""Known FFmpeg quality controls; presence is followed by an actual encode probe."""

import re

# Higher values request lower quality. Preset names and vendor controls are not equivalent.
SPECS = {
    "libx264": ("h264", 23, 12, 40, ["-preset", "medium", "-crf"]),
    "libx265": ("hevc", 24, 12, 40, ["-preset", "medium", "-crf"]),
    "libsvtav1": ("av1", 35, 16, 55, ["-preset", "6", "-svtav1-params", "lp=3", "-crf"]),
    "libaom-av1": ("av1", 35, 16, 55, ["-cpu-used", "6", "-b:v", "0", "-crf"]),
    "librav1e": ("av1", 100, 40, 180, ["-speed", "8", "-qp"]),
    "libvpx-vp9": ("vp9", 32, 12, 55, ["-deadline", "good", "-cpu-used", "4", "-b:v", "0", "-crf"]),
}
for family in ("h264", "hevc", "av1"):
    SPECS[f"{family}_nvenc"] = (
        family,
        31,
        12,
        48,
        ["-preset", "p5", "-tune", "hq", "-rc", "vbr", "-b:v", "0", "-cq"],
    )
    SPECS[f"{family}_qsv"] = (family, 25, 10, 45, ["-preset", "medium", "-global_quality"])
    SPECS[f"{family}_amf"] = (
        family,
        25,
        10,
        45,
        ["-quality", "quality", "-rc", "cqp", "-qp_i"],
    )
    SPECS[f"{family}_vaapi"] = (family, 25, 10, 45, ["-qp"])
for family in ("h264", "hevc"):
    # VideoToolbox's quality increases with q:v; invert the search direction below.
    SPECS[f"{family}_videotoolbox"] = (family, 65, 20, 95, ["-q:v"])
SPECS["vp9_qsv"] = ("vp9", 25, 10, 45, ["-global_quality"])
SPECS["vp9_vaapi"] = ("vp9", 25, 10, 45, ["-qp"])


def discover(text: str) -> tuple[list[str], list[str]]:
    names = set(re.findall(r"^\s*V\S{5}\s+(\S+)", text, re.M))
    supported = sorted(names.intersection(SPECS))
    unconfigured = sorted(
        name
        for name in names.difference(SPECS)
        if any(family in name for family in ("264", "265", "hevc", "av1", "vp9"))
    )
    return supported, unconfigured


def options(encoder: str, quality: int, pixel_format: str) -> list[str]:
    if encoder not in SPECS:
        raise ValueError(f"Unconfigured encoder: {encoder}")
    _, _, low, high, controls = SPECS[encoder]
    if not low <= quality <= high:
        raise ValueError(f"Quality outside {encoder} search range {low}..{high}")
    args = ["-c:v", encoder, *controls, str(quality)]
    if encoder.endswith("_amf"):
        args += ["-qp_p", str(quality)]
    if encoder.endswith("_vaapi"):
        # Probe the actual device rather than claiming support from the encoder listing.
        hardware_format = "p010le" if "10" in pixel_format else "nv12"
        args += [
            "-vaapi_device",
            "/dev/dri/renderD128",
            "-vf",
            f"format={hardware_format},hwupload",
        ]
    else:
        args += ["-pix_fmt", pixel_format]
    return args
