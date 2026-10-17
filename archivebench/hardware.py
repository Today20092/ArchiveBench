"""Bounded encode capability observations, separate from quality and decoding."""

import csv
import json
import os
import platform
import shutil
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import core
from .budget import deadline
from .encoders import SPECS, discover, options
from .formats import PIXEL_FORMATS, format_variants, output_video
from .hardware_limits import add_limits, check_capability

PROBE_FRAMES = 3
PROBE_SECONDS = 10
CACHE_SECONDS = 24 * 60 * 60
DEFAULT_ENCODERS = [
    "libx265",
    "libsvtav1",
    "hevc_nvenc",
    "hevc_qsv",
    "hevc_amf",
    "hevc_videotoolbox",
    "hevc_vaapi",
    "libx264",
]


def inventory(ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> dict[str, Any]:
    """List devices and compiled adapters; none of this certifies an encode."""
    parent = deadline.get()
    end = time.monotonic() + 30
    token = deadline.set(min(parent, end) if parent is not None else end)
    try:
        return _inventory(ffmpeg, ffprobe)
    finally:
        deadline.reset(token)


def _inventory(ffmpeg: str, ffprobe: str) -> dict[str, Any]:
    tools = {}
    for name, executable in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)):
        located = shutil.which(executable)
        if not located:
            raise ValueError(f"Missing executable: {executable}")
        tools[name] = {
            "path": str(Path(located).resolve()),
            "sha256": core.digest(Path(located)),
            "version": core.run([executable, "-version"], 5).strip(),
        }
    configured, other = discover(core.run([ffmpeg, "-encoders"], 5))
    devices, errors = [], []
    cpu = platform.processor()
    if shutil.which("nvidia-smi"):
        try:
            raw = core.run(
                [
                    "nvidia-smi",
                    "--query-gpu=index,uuid,name,pci.device_id,driver_version,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                5,
            )
            nvidia = []
            for row in csv.reader(raw.splitlines(), skipinitialspace=True):
                if len(row) != 6 or not row[0].isdigit():
                    raise ValueError("Unexpected nvidia-smi inventory")
                nvidia.append(
                    dict(
                        zip(
                            ("index", "uuid", "name", "pci_device_id", "driver", "memory_mib"), row
                        ),
                        vendor="NVIDIA",
                    )
                )
            devices.extend(nvidia)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            errors.append(f"NVIDIA inventory unavailable: {error}")
    # Include integrated/other vendors as well; AdapterRAM is not reliable for large VRAM.
    if platform.system() == "Windows":
        try:
            raw = core.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    "Get-CimInstance Win32_VideoController | Select-Object Name,PNPDeviceID,DriverVersion | ConvertTo-Json -Compress",
                ],
                5,
            )
            rows = json.loads(raw or "[]")
            for row in rows if isinstance(rows, list) else [rows]:
                devices.append(
                    {
                        "name": row["Name"],
                        "device_id": row["PNPDeviceID"],
                        "driver": row["DriverVersion"],
                        "provider": "Windows",
                    }
                )
        except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
            errors.append(f"Display inventory unavailable: {error}")
        try:
            cpu = (
                core.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-NonInteractive",
                        "-Command",
                        "Get-CimInstance Win32_Processor | Select-Object -ExpandProperty Name",
                    ],
                    5,
                ).strip()
                or cpu
            )
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            pass
    if platform.system() == "Darwin":
        try:
            cpu = core.run(["sysctl", "-n", "machdep.cpu.brand_string"], 5).strip()
            displays = json.loads(core.run(["system_profiler", "SPDisplaysDataType", "-json"], 5))
            for row in displays.get("SPDisplaysDataType", []):
                devices.append({"name": row.get("sppci_model", "Unknown"), "vendor": "Apple"})
        except (
            OSError,
            ValueError,
            TypeError,
            AttributeError,
            RuntimeError,
            subprocess.TimeoutExpired,
        ):
            errors.append("Apple display inventory unavailable")
    return add_limits(
        {
            "platform": platform.platform(),
            "cpu": cpu,
            "apple_chip": cpu if platform.system() == "Darwin" else None,
            "logical_cpus": os.cpu_count(),
            "devices": devices,
            "inventory_errors": errors,
            "tools": tools,
            "configured": configured,
            "unconfigured": other,
            "libvmaf": "libvmaf" in core.run([ffmpeg, "-filters"], 5),
            "decode": {"mode": "software", "hardware_support": "not-probed"},
            "device_selection": "existing FFmpeg adapter default; not a per-device certification",
            "capability_table_sha256": core.digest(Path(__file__).with_name("hardware_limits.py")),
            "driver_query_sha256": {
                name: core.digest(Path(__file__).with_name(name))
                for name in (
                    "driver_query.py",
                    "_driver_nvidia.py",
                    "_driver_amd.py",
                    "_driver_apple.py",
                )
            },
        },
        core.run,
    )


def failure_status(message: str) -> str:
    """Only explicit capability rejections are definitive, never busy/OOM/driver errors."""
    message = message.lower()
    if any(
        text in message
        for text in (
            "out of memory",
            "busy",
            "driver",
            "cannot load",
            "failed to load",
            "permission denied",
        )
    ):
        return "probe-failed"
    return (
        "unsupported"
        if any(
            text in message
            for text in (
                "does not support yuv422",
                "does not support yuv444",
                "10 bit encode not supported",
                "yuv422p not supported",
                "yuv422p10le not supported",
                "codec not supported",
                "unsupported pixel format",
                "specified pixel format",
            )
        )
        else "probe-failed"
    )


def probe_encode(
    hardware: dict[str, Any],
    encoder: str,
    quality: int,
    target: dict[str, Any],
    *,
    refresh: bool = False,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Three synthetic frames at requested dimensions/rate, then inspect actual output."""
    pixel = target["pix_fmt"]
    width, height = target["width"], target["height"]
    fps = str(Fraction(target.get("fps", target.get("avg_frame_rate", "0/1"))))
    if (
        pixel not in PIXEL_FORMATS[1:]
        or not (0 < width <= 16384 and 0 < height <= 16384)
        or Fraction(fps) <= 0
    ):
        raise ValueError(
            "Capability probe requires supported chroma/depth, positive dimensions and frame rate"
        )
    controls = options(encoder, quality, pixel)
    request = {
        "encoder": encoder,
        "quality": quality,
        "pix_fmt": pixel,
        "width": width,
        "height": height,
        "fps": fps,
        "controls": controls,
    }
    row = {**request, "status": "unknown", "cached": False}
    evidence = check_capability(hardware, encoder, pixel)
    row["capability"] = evidence
    if evidence["status"] == "unsupported":
        return {**row, "status": "unsupported", "reason": evidence["reason"]}
    identity = core.fingerprint(
        {
            "protocol": 1,
            "probe_sha256": core.digest(Path(__file__)),
            "hardware": hardware,
            "request": request,
            "adapter": SPECS[encoder],
            "frames": PROBE_FRAMES,
        }
    )
    cache_dir = (
        cache_dir
        or Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache"))
        / "ArchiveBench"
        / "capabilities"
    )
    cache = cache_dir / (identity + ".json")
    # Missing device identity cannot safely certify hardware across invocations.
    cacheable = encoder.startswith("lib") or bool(
        hardware["devices"] and not hardware["inventory_errors"]
    )
    if cacheable and not refresh:
        try:
            saved = json.loads(cache.read_text(encoding="utf-8"))
            if (
                saved["identity"] == identity
                and 0 <= time.time() - saved["observed_at"] < CACHE_SECONDS
                and saved["result"]["status"] in ("verified", "unsupported")
                and all(saved["result"].get(key) == value for key, value in request.items())
            ):
                return {**saved["result"], "cached": True}
        except (OSError, ValueError, KeyError, TypeError):
            pass
    started = time.monotonic()
    parent = deadline.get()
    token = deadline.set(
        min(parent, started + PROBE_SECONDS) if parent is not None else started + PROBE_SECONDS
    )
    try:
        with tempfile.TemporaryDirectory(prefix="archivebench-capability-") as scratch:
            path = Path(scratch) / "probe.mkv"
            ffmpeg, ffprobe = (hardware["tools"][name]["path"] for name in ("ffmpeg", "ffprobe"))
            # Hardware may use an equivalent memory layout (p010/nv12). Verify decoded output
            # rather than forbidding those layouts; any chroma/depth fallback fails below.
            core.run(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-nostdin",
                    "-v",
                    "verbose",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=size={width}x{height}:rate={fps},format={pixel}",
                    "-frames:v",
                    str(PROBE_FRAMES),
                    *controls,
                    "-g",
                    str(max(1, round(float(Fraction(fps)) * 8))),
                    "-f",
                    "matroska",
                    str(path),
                ],
                PROBE_SECONDS,
            )
            actual = core.primary(core.probe(path, ffprobe))
            expected = {
                "codec_name": SPECS[encoder][0],
                "pix_fmt": pixel,
                "width": width,
                "height": height,
            }
            if any(actual.get(key) != value for key, value in expected.items()) or Fraction(
                actual["avg_frame_rate"]
            ) != Fraction(fps):
                row.update(
                    status="unsupported",
                    reason="Encoded output differs from requested codec/chroma/depth/dimensions/frame rate",
                )
            else:
                row.update(
                    status="verified",
                    reason="Synthetic encode and output format check passed",
                    actual=expected,
                )
    except subprocess.TimeoutExpired:
        row.update(
            status="probe-failed", reason="Probe deadline reached; capability remains unknown"
        )
    except (OSError, ValueError, KeyError, RuntimeError) as error:
        message = str(error)
        status = failure_status(message)
        explanation = [line for line in message.splitlines() if "support" in line.lower()]
        row.update(
            status=status,
            reason="\n".join(explanation)[:1500]
            if status == "unsupported" and explanation
            else message[-1500:],
        )
    finally:
        deadline.reset(token)
    row["probe_seconds"] = time.monotonic() - started
    if cacheable and row["status"] in ("verified", "unsupported"):
        try:
            cache.parent.mkdir(parents=True, exist_ok=True)
            # Per-writer temporary names avoid concurrent terminal sessions sharing a .tmp file.
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=cache.parent, delete=False
            ) as stream:
                temporary = Path(stream.name)
                json.dump({"identity": identity, "observed_at": time.time(), "result": row}, stream)
            try:
                temporary.replace(cache)
            finally:
                temporary.unlink(missing_ok=True)
        except OSError:
            pass  # Cache is optional; an unwritable directory must not block verification.
    return row


def check_config(
    config: dict[str, Any],
    *,
    refresh: bool = False,
    seconds: float = 30,
    hardware: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Report every requested combination; exhausted checks are explicitly unknown."""
    from .experiments import fixed_settings

    end = time.monotonic() + seconds
    parent = deadline.get()
    token = deadline.set(min(parent, end) if parent is not None else end)
    try:
        if hardware is None:
            hardware = inventory(config.get("ffmpeg", "ffmpeg"), config.get("ffprobe", "ffprobe"))
        encoders = config.get("encoders") or hardware["configured"]
        settings = (
            fixed_settings({**config, "encoders": encoders})
            if config.get("strategy") == "fixed"
            else {e: [config.get("quality_overrides", {}).get(e, SPECS[e][1])] for e in encoders}
        )
        rows, seen = [], {}
        sources = {}
        for sample in config["samples"]:
            if sample["path"] not in sources:
                try:
                    sources[sample["path"]] = core.primary(
                        core.probe(Path(sample["path"]), config.get("ffprobe", "ffprobe"))
                    )
                except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                    sources[sample["path"]] = {"error": str(error)}
        for sample in config["samples"]:
            video = sources[sample["path"]]
            for variant in format_variants(config):
                try:
                    if "error" in video:
                        raise ValueError(video["error"])
                    target = output_video(video, variant)
                except ValueError as error:
                    rows.extend(
                        {
                            "encoder": e,
                            "quality": q,
                            "source": sample["path"],
                            "variant": variant["id"],
                            "status": "unknown",
                            "reason": str(error),
                        }
                        for e, qualities in settings.items()
                        for q in qualities
                    )
                    continue
                for encoder, qualities in settings.items():
                    for quality in qualities:
                        key = (
                            encoder,
                            quality,
                            target["pix_fmt"],
                            target["width"],
                            target["height"],
                            video["avg_frame_rate"],
                        )
                        if key not in seen:
                            evidence = check_capability(hardware, encoder, target["pix_fmt"])
                            if evidence["status"] == "unsupported":
                                seen[key] = {
                                    "encoder": encoder,
                                    "quality": quality,
                                    "status": "unsupported",
                                    "reason": evidence["reason"],
                                    "capability": evidence,
                                }
                            elif time.monotonic() >= (deadline.get() or end):
                                seen[key] = {
                                    "encoder": encoder,
                                    "quality": quality,
                                    "status": "unknown",
                                    "reason": "Discovery allowance exhausted",
                                }
                            else:
                                seen[key] = probe_encode(
                                    hardware, encoder, quality, target, refresh=refresh
                                )
                        rows.append(
                            {
                                **seen[key],
                                "source": sample["path"],
                                "variant": variant["id"],
                                "source_pix_fmt": video["pix_fmt"],
                                "pix_fmt": target["pix_fmt"],
                                "width": target["width"],
                                "height": target["height"],
                                "fps": video["avg_frame_rate"],
                            }
                        )
        verified = [
            e
            for e in encoders
            if rows and all(r["status"] == "verified" for r in rows if r["encoder"] == e)
        ]
        return {
            "hardware": hardware,
            "checks": rows,
            "verified_encoders": verified,
            "limits": {
                "frames_per_probe": PROBE_FRAMES,
                "seconds_per_probe": PROBE_SECONDS,
                "total_seconds": seconds,
            },
            "note": "Encode format support only; no quality, throughput or hardware decode certification. Actual footage is checked again.",
        }
    finally:
        deadline.reset(token)


def availability(
    config: dict[str, Any],
    *,
    refresh: bool = False,
    seconds: float = 30,
    hardware: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inventory failure must not masquerade as an unsupported encoder."""
    try:
        return check_config(config, refresh=refresh, seconds=seconds, hardware=hardware)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        return {"checks": [], "verified_encoders": [], "status": "unknown", "reason": str(error)}


def suggested_encoders(report: dict[str, Any]) -> list[str]:
    """A small starting comparison, only after every selected format passes."""
    verified = report["verified_encoders"]
    return [name for name in DEFAULT_ENCODERS if name in verified][:3]


def availability_summary(report: dict[str, Any]) -> str:
    """Human-facing evidence without driver identifiers and full build diagnostics."""
    rows = []
    for row in report["checks"]:
        requested = f"{row.get('source_pix_fmt', '?')} -> {row.get('pix_fmt', '?')} {row.get('width', '?')}x{row.get('height', '?')} @ {row.get('fps', '?')}"
        rows.append(
            f"{Path(row['source']).name} / {row['variant']} / {row['encoder']} Q{row['quality']}: {requested}: {row['status']}"
            + (" (cached)" if row.get("cached") else "")
        )
        if row["status"] != "verified":
            rows.append("  " + (row.get("reason") or "No evidence").splitlines()[0])
    return "\n".join(rows) or report.get("reason", "No capability observations")
