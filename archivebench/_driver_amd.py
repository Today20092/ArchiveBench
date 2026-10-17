"""AMF ComponentCaps queries on each AMD DXGI adapter (Windows x64)."""

import ctypes as C
import platform
from contextlib import ExitStack

from .driver_query import (
    GUID,
    INT,
    UINT,
    PTR,
    PIXELS,
    bind,
    bounded_count,
    checked,
    library,
    method,
)

COMPONENTS = {
    "h264": "AMFVideoEncoderVCE_AVC",
    "hevc": "AMFVideoEncoderHW_HEVC",
    "av1": "AMFVideoEncoderHW_AV1",
}


class AdapterDescription(C.Structure):
    _fields_ = [
        ("name", C.c_wchar * 128),
        ("vendor", UINT),
        ("device", UINT),
        ("subsystem", UINT),
        ("revision", UINT),
        ("video_memory", C.c_size_t),
        ("system_memory", C.c_size_t),
        ("shared_memory", C.c_size_t),
        ("luid_low", UINT),
        ("luid_high", INT),
        ("flags", UINT),
    ]


def format_support(formats: list[tuple[int, bool]]) -> dict[str, bool | None]:
    native = {value for value, supported in formats if supported}
    layouts = ({1, 2, 7}, {10}, {9, 12}, {14})
    return {pixel: True if native & aliases else None for pixel, aliases in zip(PIXELS, layouts)}


def query() -> list[dict]:
    if platform.system() != "Windows" or C.sizeof(C.c_wchar) != 2:
        raise ValueError("AMF query currently requires Windows x64")
    runtime = library("amfrt64.dll", "")
    version, factory = C.c_uint64(), PTR()
    checked(
        bind(runtime, "AMFQueryVersion", INT, C.POINTER(C.c_uint64))(C.byref(version)),
        "AMF version",
    )
    if version.value >> 48 != 1:
        raise ValueError("Unsupported AMF interface major version")
    checked(
        bind(runtime, "AMFInit", INT, C.c_uint64, C.POINTER(PTR))(version, C.byref(factory)),
        "AMF initialization",
    )
    dxgi, d3d = library("dxgi.dll", ""), library("d3d11.dll", "")
    dxgi_factory = PTR()
    iid = GUID.parse("770aae78-f26f-4dba-a829-253c83d1b387")
    checked(
        bind(dxgi, "CreateDXGIFactory1", INT, C.POINTER(GUID), C.POINTER(PTR))(
            C.byref(iid), C.byref(dxgi_factory)
        ),
        "DXGI factory",
    )
    rows = []
    with ExitStack() as outer:
        outer.callback(method, dxgi_factory, 2, UINT, ())
        for index in range(33):
            adapter = PTR()
            status = method(dxgi_factory, 12, INT, (UINT, C.POINTER(PTR)), index, C.byref(adapter))
            if status & 0xFFFFFFFF == 0x887A0002:
                break
            checked(status, "DXGI adapter enumeration")
            if index == 32:
                method(adapter, 2, UINT, ())
                raise ValueError("Too many DXGI adapters")
            with ExitStack() as stack:
                stack.callback(method, adapter, 2, UINT, ())
                description = AdapterDescription()
                checked(
                    method(
                        adapter, 10, INT, (C.POINTER(AdapterDescription),), C.byref(description)
                    ),
                    "DXGI identity",
                )
                if description.vendor != 0x1002:
                    continue
                row = {
                    "id": f"{description.luid_high & 0xFFFFFFFF:08x}:{description.luid_low:08x}",
                    "name": description.name,
                    "driver_version": version.value,
                    "codecs": {},
                }
                rows.append(row)
                device, context = PTR(), PTR()
                try:
                    checked(
                        bind(
                            d3d,
                            "D3D11CreateDevice",
                            INT,
                            PTR,
                            UINT,
                            PTR,
                            UINT,
                            PTR,
                            UINT,
                            UINT,
                            C.POINTER(PTR),
                            PTR,
                            PTR,
                        )(adapter, 0, None, 0, None, 0, 7, C.byref(device), None, None),
                        "D3D11 device",
                    )
                    stack.callback(method, device, 2, UINT, ())
                    checked(
                        method(factory, 0, INT, (C.POINTER(PTR),), C.byref(context)), "AMF context"
                    )
                    stack.callback(method, context, 1, INT, ())
                    stack.callback(method, context, 13, INT, ())
                    checked(method(context, 18, INT, (PTR, INT), device, 110), "AMF DX11 context")
                    for codec, component_name in COMPONENTS.items():
                        with ExitStack() as component_stack:
                            component, caps, inputs = PTR(), PTR(), PTR()
                            status = method(
                                factory,
                                1,
                                INT,
                                (PTR, C.c_wchar_p, C.POINTER(PTR)),
                                context,
                                component_name,
                                C.byref(component),
                            )
                            if status != 0:
                                row["codecs"][codec] = {
                                    "formats": {},
                                    "reason": f"AMF component unavailable ({status})",
                                }
                                continue
                            component_stack.callback(method, component, 1, INT, ())
                            checked(
                                method(component, 26, INT, (C.POINTER(PTR),), C.byref(caps)),
                                "AMF capabilities",
                            )
                            component_stack.callback(method, caps, 1, INT, ())
                            acceleration = method(caps, 13, INT, ())
                            if acceleration != 0:
                                row["codecs"][codec] = {
                                    "formats": {},
                                    "reason": "AMF did not report dedicated hardware acceleration",
                                }
                                continue
                            checked(
                                method(caps, 14, INT, (C.POINTER(PTR),), C.byref(inputs)),
                                "AMF input capabilities",
                            )
                            component_stack.callback(method, inputs, 1, INT, ())
                            count = bounded_count(method(inputs, 6, INT, ()))
                            formats = []
                            for position in range(count):
                                value, native = INT(), C.c_uint8()
                                checked(
                                    method(
                                        inputs,
                                        7,
                                        INT,
                                        (INT, C.POINTER(INT), C.POINTER(C.c_uint8)),
                                        position,
                                        C.byref(value),
                                        C.byref(native),
                                    ),
                                    "AMF input format",
                                )
                                formats.append((value.value, bool(native.value)))
                            row["codecs"][codec] = {
                                "formats": format_support(formats),
                                "input_formats": formats,
                            }
                except (OSError, ValueError) as error:
                    row["reason"] = str(error)
    return rows
