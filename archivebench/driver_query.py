"""Isolated native driver queries; no frame encoding, network or SDK installation."""

import ctypes as C
import importlib
import json
import os
import platform
import subprocess
import sys
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

PIXELS = ("yuv420p", "yuv420p10le", "yuv422p", "yuv422p10le")
BACKENDS = {"nvenc": "nvidia", "amf": "amd", "videotoolbox": "apple"}
QUERY_SECONDS = 5
PTR = C.c_void_p
INT = C.c_int32
UINT = C.c_uint32
ABI = getattr(C, "WINFUNCTYPE", C.CFUNCTYPE)


class GUID(C.Structure):
    _fields_ = [
        ("data1", UINT),
        ("data2", C.c_uint16),
        ("data3", C.c_uint16),
        ("data4", C.c_ubyte * 8),
    ]

    @classmethod
    def parse(cls, text: str):
        return cls.from_buffer_copy(uuid.UUID(text).bytes_le)


def library(windows: str, linux: str):
    if os.name == "nt":
        return getattr(C, "WinDLL")(windows, winmode=0x800)
    return C.CDLL(linux)


def bind(lib, name: str, result, *arguments):
    function = getattr(lib, name)
    function.restype, function.argtypes = result, list(arguments)
    return function


def method(pointer, index: int, result, arguments: tuple, *values):
    if not pointer:
        raise ValueError("Native interface is null")
    table = C.cast(pointer, C.POINTER(C.POINTER(PTR))).contents
    if not table[index]:
        raise ValueError("Native method is unavailable")
    return ABI(result, PTR, *arguments)(table[index])(pointer, *values)


def checked(status: int, operation: str) -> None:
    if status != 0:
        raise OSError(f"{operation} failed ({status})")


def bounded_count(count: int, maximum: int = 256) -> int:
    if not 0 < count <= maximum:
        raise ValueError("Native enumeration count is invalid or empty")
    return count


def query_drivers(hardware: dict[str, Any], run: Callable[..., str]) -> dict[str, Any]:
    result = {}
    for suffix, backend in BACKENDS.items():
        if not any(name.endswith("_" + suffix) for name in hardware["configured"]):
            continue
        if backend == "apple" and platform.system() != "Darwin":
            continue
        if backend == "amd" and platform.system() != "Windows":
            continue
        try:
            # -I excludes user startup modules; the only added path is our installed package root.
            text = run(
                [
                    sys.executable,
                    "-I",
                    "-c",
                    "import sys;sys.path.insert(0,sys.argv[1]);from archivebench.driver_query import main;main(sys.argv[2])",
                    str(Path(__file__).resolve().parent.parent),
                    backend,
                ],
                QUERY_SECONDS,
            )
            if len(text) > 256_000:
                raise ValueError("Driver response is too large")
            response = json.loads(text)
            validate_response(response, backend)
            result[backend] = response
        except subprocess.TimeoutExpired:
            result[backend] = {
                "backend": backend,
                "status": "unknown",
                "reason": "Native query exceeded its five-second or remaining operation allowance",
            }
        except RuntimeError:
            result[backend] = {
                "backend": backend,
                "status": "unknown",
                "reason": "Native query process failed or crashed",
            }
        except (OSError, ValueError):
            result[backend] = {
                "backend": backend,
                "status": "unknown",
                "reason": "Native query unavailable or returned malformed evidence",
            }
    return result


def validate_response(value: Any, backend: str) -> None:
    if not isinstance(value, dict) or value.get("backend") != backend or value.get("version") != 1:
        raise ValueError("Invalid driver response")
    if value.get("status") == "unknown":
        return
    devices = value.get("devices")
    if (
        value.get("status") != "queried"
        or value.get("complete") is not True
        or not isinstance(devices, list)
        or not 0 < len(devices) <= 32
    ):
        raise ValueError("Incomplete driver enumeration")
    for device in devices:
        if (
            not isinstance(device, dict)
            or not isinstance(device.get("id"), str)
            or not isinstance(device.get("codecs"), dict)
        ):
            raise ValueError("Invalid driver device")
        for codec, facts in device["codecs"].items():
            if codec not in ("h264", "hevc", "av1") or not isinstance(facts, dict):
                raise ValueError("Invalid codec evidence")
            formats = facts.get("formats", {})
            if not isinstance(formats, dict):
                raise ValueError("Invalid format evidence")
            for pixel, supported in formats.items():
                if pixel not in PIXELS or (supported is not None and type(supported) is not bool):
                    raise ValueError("Invalid format evidence")


def driver_verdict(hardware: dict[str, Any], encoder: str, pixel: str) -> dict[str, Any] | None:
    backend = BACKENDS.get(encoder.rsplit("_", 1)[-1])
    query = hardware.get("driver_queries", {}).get(backend, {})
    if query.get("status") != "queried" or query.get("complete") is not True:
        return None
    codec = encoder.rsplit("_", 1)[0]
    values = [
        device.get("codecs", {}).get(codec, {}).get("formats", {}).get(pixel)
        for device in query["devices"]
    ]
    if not values or all(value is None for value in values):
        return None
    status = (
        "unsupported"
        if all(value is False for value in values)
        else "candidate"
        if all(value is True for value in values)
        else "unknown"
    )
    return {
        "status": status,
        "source": "driver",
        "backend": backend,
        "reason": "Driver reports this codec/format unsupported on every enumerated device"
        if status == "unsupported"
        else "Driver permits this format; exact encode verification required"
        if status == "candidate"
        else "Mixed or incomplete per-device driver evidence; actual device selection needs a probe",
        "devices": [
            {"id": device["id"], "supported": value}
            for device, value in zip(query["devices"], values)
        ],
    }


def main(backend: str) -> None:
    try:
        if os.name == "nt":
            bind(library("kernel32.dll", ""), "SetErrorMode", UINT, UINT)(0x8003)
        if backend not in BACKENDS.values() or C.sizeof(PTR) != 8:
            raise ValueError("Native query backend or architecture unavailable")
        module = importlib.import_module("archivebench._driver_" + backend)
        result = {
            "version": 1,
            "backend": backend,
            "status": "queried",
            "complete": True,
            "devices": module.query(),
        }
        validate_response(result, backend)
    except Exception as error:
        result = {"version": 1, "backend": backend, "status": "unknown", "reason": str(error)[:300]}
    print(json.dumps(result))
