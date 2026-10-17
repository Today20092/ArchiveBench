"""VideoToolbox hardware encoder enumeration and supported-property queries."""

import ctypes as C
import platform
import plistlib

from .driver_query import INT, UINT, PTR, PIXELS, bind, bounded_count, checked

CODECS = {
    name: int.from_bytes(value, "big")
    for name, value in (("h264", b"avc1"), ("hevc", b"hvc1"), ("av1", b"av01"))
}


def codec_evidence(entries: list[dict]) -> dict:
    complete = all(
        isinstance(row, dict)
        and type(row.get("IsHardwareAccelerated")) is bool
        and type(row.get("CodecType")) is int
        for row in entries
    )
    result = {}
    for codec, code in CODECS.items():
        matching = [
            row
            for row in entries
            if isinstance(row, dict)
            and row.get("CodecType") == code
            and row.get("IsHardwareAccelerated") is True
        ]
        available = True if matching else False if complete else None
        result[codec] = {
            "available": available,
            "formats": dict.fromkeys(PIXELS, False if available is False else None),
            "encoder_ids": [
                row["EncoderID"] for row in matching if isinstance(row.get("EncoderID"), str)
            ],
        }
    return result


def query() -> list[dict]:
    if platform.system() != "Darwin":
        raise ValueError("VideoToolbox query requires macOS")
    cf = C.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    vt = C.CDLL("/System/Library/Frameworks/VideoToolbox.framework/VideoToolbox")
    release = bind(cf, "CFRelease", None, PTR)

    def decode(value):
        error = PTR()
        data = bind(
            cf, "CFPropertyListCreateData", PTR, PTR, PTR, C.c_long, C.c_ulong, C.POINTER(PTR)
        )(None, value, 100, 0, C.byref(error))
        try:
            if not data:
                raise ValueError("VideoToolbox properties could not be read")
            size = bind(cf, "CFDataGetLength", C.c_long, PTR)(data)
            if not 0 < size <= 1_000_000:
                raise ValueError("VideoToolbox property response size is invalid")
            pointer = bind(cf, "CFDataGetBytePtr", PTR, PTR)(data)
            return plistlib.loads(C.string_at(pointer, size))
        finally:
            if data:
                release(data)
            if error:
                release(error)

    encoders = PTR()
    checked(
        bind(vt, "VTCopyVideoEncoderList", INT, PTR, C.POINTER(PTR))(None, C.byref(encoders)),
        "VideoToolbox encoder list",
    )
    try:
        entries = decode(encoders)
    finally:
        if encoders:
            release(encoders)
    if not isinstance(entries, list):
        raise ValueError("Unexpected VideoToolbox encoder list")
    bounded_count(len(entries))
    codecs = codec_evidence(entries)
    keys = (PTR * 1)(
        PTR.in_dll(vt, "kVTVideoEncoderSpecification_RequireHardwareAcceleratedVideoEncoder").value
    )
    values = (PTR * 1)(PTR.in_dll(cf, "kCFBooleanTrue").value)
    spec = bind(
        cf, "CFDictionaryCreate", PTR, PTR, C.POINTER(PTR), C.POINTER(PTR), C.c_long, PTR, PTR
    )(None, keys, values, 1, None, None)
    try:
        if not spec:
            raise ValueError("VideoToolbox hardware selection unavailable")
        for codec, facts in codecs.items():
            if facts["available"] is not True:
                continue
            identifier, properties = PTR(), PTR()
            try:
                status = bind(
                    vt,
                    "VTCopySupportedPropertyDictionaryForEncoder",
                    INT,
                    INT,
                    INT,
                    UINT,
                    PTR,
                    C.POINTER(PTR),
                    C.POINTER(PTR),
                )(1920, 1080, CODECS[codec], spec, C.byref(identifier), C.byref(properties))
                checked(status, "VideoToolbox supported properties")
                decoded = decode(properties)
                profile = decoded.get("ProfileLevel", {})
                facts["profile_levels"] = (
                    [
                        value
                        for value in profile.get("SupportedValueList", [])
                        if isinstance(value, str)
                    ][:256]
                    if isinstance(profile, dict)
                    else []
                )
                facts["property_query_size"] = [1920, 1080]
            except (OSError, ValueError, TypeError, AttributeError) as error:
                facts["reason"] = str(error)
            finally:
                if identifier:
                    release(identifier)
                if properties:
                    release(properties)
    finally:
        if spec:
            release(spec)
    return [
        {"id": "videotoolbox-hardware", "name": "VideoToolbox hardware encoders", "codecs": codecs}
    ]
