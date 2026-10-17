"""NVENC 13.0 ABI queries, negotiated down to the installed driver's API version.

ABI reference: nv-codec-headers n13.0.19.0/include/ffnvcodec/nvEncodeAPI.h.
"""

import ctypes as C

from .driver_query import ABI, GUID, INT, UINT, PTR, PIXELS, bind, bounded_count, checked, library

CODECS = {
    "h264": "6bc82762-4e63-4ca4-aa85-1e50f321f6bf",
    "hevc": "790cdc88-4522-4d7b-9425-bda9975f7603",
    "av1": "0a352289-0aa7-4759-862d-5d15cd16d254",
}
FORMATS = (1, 0x10000, 0x40000001, 0x40000002)


class FunctionList(C.Structure):
    _fields_ = [("version", UINT), ("reserved", UINT), ("functions", PTR * 318)]


class OpenSession(C.Structure):
    _fields_ = [
        ("version", UINT),
        ("device_type", UINT),
        ("device", PTR),
        ("reserved", PTR),
        ("api_version", UINT),
        ("reserved1", UINT * 253),
        ("reserved2", PTR * 64),
    ]


class Caps(C.Structure):
    _fields_ = [("version", UINT), ("query", UINT), ("reserved", UINT * 62)]


def format_support(
    formats: set[int], ten_bit: bool | None, chroma422: bool | None
) -> dict[str, bool | None]:
    result = {}
    for pixel, format_id in zip(PIXELS, FORMATS):
        requirements = [format_id in formats]
        if "10" in pixel:
            requirements.append(ten_bit)
        if "422" in pixel:
            requirements.append(chroma422)
        result[pixel] = False if False in requirements else None if None in requirements else True
    return result


def query() -> list[dict]:
    cuda = library("nvcuda.dll", "libcuda.so.1")
    nvenc = library("nvEncodeAPI64.dll", "libnvidia-encode.so.1")
    checked(bind(cuda, "cuInit", INT, UINT)(0), "cuInit")
    maximum = UINT()
    checked(
        bind(nvenc, "NvEncodeAPIGetMaxSupportedVersion", INT, C.POINTER(UINT))(C.byref(maximum)),
        "NVENC API version",
    )
    negotiated = min(maximum.value, 0xD0)
    if negotiated < 0xB0:
        raise ValueError("NVENC API older than supported query ABI")
    api = (negotiated >> 4) | ((negotiated & 15) << 24)
    table = FunctionList(version=api | (2 << 16) | (7 << 28))
    checked(
        bind(nvenc, "NvEncodeAPICreateInstance", INT, C.POINTER(FunctionList))(C.byref(table)),
        "NVENC function table",
    )

    def call(index, arguments, *values):
        if not table.functions[index]:
            raise ValueError("NVENC query function unavailable")
        return ABI(INT, *arguments)(table.functions[index])(*values)

    count = INT()
    checked(bind(cuda, "cuDeviceGetCount", INT, C.POINTER(INT))(C.byref(count)), "CUDA enumeration")
    rows = []
    for index in range(bounded_count(count.value, 32)):
        device, context, session = INT(), PTR(), PTR()
        checked(
            bind(cuda, "cuDeviceGet", INT, C.POINTER(INT), INT)(C.byref(device), index),
            "CUDA device",
        )
        name, bus = C.create_string_buffer(256), C.create_string_buffer(32)
        checked(
            bind(cuda, "cuDeviceGetName", INT, PTR, INT, INT)(name, len(name), device), "CUDA name"
        )
        checked(
            bind(cuda, "cuDeviceGetPCIBusId", INT, PTR, INT, INT)(bus, len(bus), device),
            "CUDA PCI identity",
        )
        row = {
            "id": bus.value.decode(),
            "name": name.value.decode(),
            "api_version": api,
            "codecs": {},
        }
        rows.append(row)
        try:
            checked(
                bind(cuda, "cuCtxCreate_v2", INT, C.POINTER(PTR), UINT, INT)(
                    C.byref(context), 0, device
                ),
                "CUDA context",
            )
            params = OpenSession(
                version=api | (1 << 16) | (7 << 28), device_type=1, device=context, api_version=api
            )
            checked(
                call(
                    29, (C.POINTER(OpenSession), C.POINTER(PTR)), C.byref(params), C.byref(session)
                ),
                "NVENC session",
            )
            total = UINT()
            checked(call(1, (PTR, C.POINTER(UINT)), session, C.byref(total)), "NVENC codec count")
            guids = (GUID * bounded_count(total.value))()
            checked(
                call(
                    4,
                    (PTR, C.POINTER(GUID), UINT, C.POINTER(UINT)),
                    session,
                    guids,
                    len(guids),
                    C.byref(total),
                ),
                "NVENC codecs",
            )
            bounded_count(total.value, len(guids))
            available = {bytes(guid) for guid in guids[: total.value]}
            for codec, text in CODECS.items():
                guid = GUID.parse(text)
                if bytes(guid) not in available:
                    row["codecs"][codec] = {"formats": dict.fromkeys(PIXELS, False)}
                    continue
                checked(
                    call(5, (PTR, GUID, C.POINTER(UINT)), session, guid, C.byref(total)),
                    "NVENC format count",
                )
                formats = (UINT * bounded_count(total.value))()
                checked(
                    call(
                        6,
                        (PTR, GUID, C.POINTER(UINT), UINT, C.POINTER(UINT)),
                        session,
                        guid,
                        formats,
                        len(formats),
                        C.byref(total),
                    ),
                    "NVENC formats",
                )
                bounded_count(total.value, len(formats))
                caps = []
                for flag in (39, 59):
                    parameter, value = Caps(version=api | (1 << 16) | (7 << 28), query=flag), INT()
                    status = call(
                        7,
                        (PTR, GUID, C.POINTER(Caps), C.POINTER(INT)),
                        session,
                        guid,
                        C.byref(parameter),
                        C.byref(value),
                    )
                    caps.append(bool(value.value) if status == 0 else None)
                row["codecs"][codec] = {
                    "formats": format_support(set(formats[: total.value]), *caps),
                    "input_formats": list(formats[: total.value]),
                    "ten_bit": caps[0],
                    "chroma422": caps[1],
                }
        except (OSError, ValueError) as error:
            row["reason"] = str(error)
        finally:
            if session:
                call(27, (PTR,), session)
            if context:
                bind(cuda, "cuCtxDestroy_v2", INT, PTR)(context)
    return rows
