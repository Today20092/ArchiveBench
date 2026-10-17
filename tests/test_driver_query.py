import ctypes as C
import json
import platform
import subprocess
from copy import deepcopy

import pytest

from archivebench import driver_query as dq, hardware_limits as limits
from archivebench import _driver_nvidia as nv, _driver_amd as amd, _driver_apple as apple


def response(*values, backend="nvidia"):
    return {
        "version": 1,
        "backend": backend,
        "status": "queried",
        "complete": True,
        "devices": [
            {"id": str(index), "codecs": {"hevc": {"formats": dict.fromkeys(dq.PIXELS, value)}}}
            for index, value in enumerate(values)
        ],
    }


def snapshot(native):
    return {
        "configured": ["hevc_nvenc"],
        "tools": {"ffmpeg": {"path": "ffmpeg"}},
        "encoder_pixel_formats": {"hevc_nvenc": ["nv12", "p010le", "nv16", "p210le"]},
        "driver_queries": {"nvidia": native},
        "devices": [{"name": "GeForce RTX 3070 Ti", "vendor": "NVIDIA"}],
        "inventory_errors": [],
        "visibility": {},
    }


def test_native_facts_override_model_table_and_intersect_ffmpeg():
    state = snapshot(response(True))
    check = limits.check_capability(state, "hevc_nvenc", "yuv422p10le")
    assert check["source"] == "driver" and check["status"] == "candidate"
    state["encoder_pixel_formats"]["hevc_nvenc"] = ["nv12", "p010le"]
    check = limits.check_capability(state, "hevc_nvenc", "yuv422p10le")
    assert check["source"] == "ffmpeg" and check["status"] == "unsupported"
    assert check["driver_evidence"]["status"] == "candidate"
    state = snapshot(response(False))
    state["devices"][0]["name"] = "GeForce RTX 5090"
    check = limits.check_capability(state, "hevc_nvenc", "yuv420p")
    assert check["source"] == "driver" and check["status"] == "unsupported"


@pytest.mark.parametrize(
    "values,status",
    [
        ((True,), "candidate"),
        ((False, False), "unsupported"),
        ((False, True), "unknown"),
        ((False, None), "unknown"),
    ],
)
def test_multi_device_evidence_does_not_inherit_model_rejection(values, status):
    check = limits.check_capability(snapshot(response(*values)), "hevc_nvenc", "yuv422p10le")
    assert check["source"] == "driver" and check["status"] == status


@pytest.mark.parametrize("native", [{"status": "unknown"}, response(None)])
def test_unavailable_or_inconclusive_queries_use_manufacturer_fallback(native):
    check = limits.check_capability(snapshot(native), "hevc_nvenc", "yuv422p10le")
    assert check["source"] == "manufacturer-fallback" and check["status"] == "unsupported"


def test_driver_query_precedes_ffmpeg_help_and_is_process_isolated():
    state, calls = snapshot({}), []

    def run(args, timeout):
        calls.append((args, timeout))
        return (
            json.dumps(response(True))
            if "-I" in args
            else "Supported pixel formats: nv12 p010le nv16 p210le"
        )

    enriched = limits.add_limits(state, run)
    assert "-I" in calls[0][0] and calls[0][1] == 5
    assert calls[0][0][-1] == "nvidia" and "-h" in calls[1][0]
    assert enriched["driver_queries"]["nvidia"]["status"] == "queried"


@pytest.mark.parametrize(
    "failure", [OSError("missing"), RuntimeError("crashed"), subprocess.TimeoutExpired("worker", 5)]
)
def test_failed_processes_remain_unknown(failure):
    def run(*args):
        raise failure

    query = dq.query_drivers(snapshot({}), run)["nvidia"]
    assert query["status"] == "unknown" and query["reason"]


@pytest.mark.parametrize(
    "bad",
    ["not json", "null", "[]", '{"version":1}', "x" * 256001],
    ids=["invalid-json", "null", "array", "missing-fields", "oversized"],
)
def test_malformed_process_output_is_unknown(bad):
    assert dq.query_drivers(snapshot({}), lambda *a: bad)["nvidia"]["status"] == "unknown"


@pytest.mark.parametrize(
    "alter",
    [
        lambda r: r.update(complete=False),
        lambda r: r.update(devices=[]),
        lambda r: r["devices"][0]["codecs"]["hevc"].update(formats=[]),
        lambda r: r["devices"][0]["codecs"]["hevc"]["formats"].update(yuv420p=0),
    ],
)
def test_untrusted_native_schema_cannot_claim_unsupported(alter):
    value = response(False)
    alter(value)
    assert (
        dq.query_drivers(snapshot({}), lambda *a: json.dumps(value))["nvidia"]["status"]
        == "unknown"
    )


def test_native_abi_sizes_and_versions():
    assert C.sizeof(dq.GUID) == 16 and C.alignment(dq.GUID) == 4
    assert bytes(dq.GUID.parse(nv.CODECS["hevc"]))[:4] == bytes.fromhex("88dc0c79")
    if C.sizeof(C.c_void_p) == 8:
        assert C.sizeof(nv.FunctionList) == 2552
        assert nv.FunctionList.functions.offset == 8
        assert C.sizeof(nv.OpenSession) == 1552
        assert nv.OpenSession.api_version.offset == 24
        assert C.sizeof(nv.Caps) == 256
    if platform.system() == "Windows":
        assert C.sizeof(amd.AdapterDescription) == 312
        assert amd.AdapterDescription.luid_low.offset == 296


def test_nvenc_input_formats_and_capability_flags_are_both_required():
    formats = nv.format_support(set(nv.FORMATS), True, False)
    assert formats == {"yuv420p": True, "yuv420p10le": True, "yuv422p": False, "yuv422p10le": False}
    assert nv.format_support(set(nv.FORMATS), None, True)["yuv422p10le"] is None
    assert nv.format_support({1}, True, True)["yuv422p"] is False


def test_amf_native_input_layouts_do_not_certify_converted_inputs():
    formats = amd.format_support([(1, True), (10, True), (9, False)])
    assert formats == {"yuv420p": True, "yuv420p10le": True, "yuv422p": None, "yuv422p10le": None}


def test_apple_hardware_codec_presence_does_not_invent_format_support():
    rows = [
        {
            "CodecType": apple.CODECS["hevc"],
            "IsHardwareAccelerated": True,
            "EncoderID": "hardware-hevc",
        },
        {"CodecType": apple.CODECS["h264"], "IsHardwareAccelerated": False},
    ]
    codecs = apple.codec_evidence(rows)
    assert codecs["hevc"]["available"] is True
    assert all(value is None for value in codecs["hevc"]["formats"].values())
    assert all(value is False for value in codecs["h264"]["formats"].values())
    incomplete = deepcopy(rows)
    incomplete[1].pop("IsHardwareAccelerated")
    assert apple.codec_evidence(incomplete)["h264"]["available"] is None


def test_unknown_worker_backend_returns_structured_failure(capsys):
    dq.main("unrecognized")
    assert json.loads(capsys.readouterr().out)["status"] == "unknown"


def test_native_query_changes_invalidate_probe_cache(tmp_path, monkeypatch):
    from archivebench import hardware as hw

    state = snapshot(response(True))
    state.update(
        inventory_errors=[], tools={"ffmpeg": {"path": "ffmpeg"}, "ffprobe": {"path": "ffprobe"}}
    )
    calls = []
    monkeypatch.setattr(hw.core, "run", lambda *args: calls.append(args) or "")
    monkeypatch.setattr(
        hw.core,
        "probe",
        lambda *args: {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "pix_fmt": "yuv420p",
                    "width": 64,
                    "height": 64,
                    "avg_frame_rate": "24",
                }
            ]
        },
    )
    target = {"pix_fmt": "yuv420p", "width": 64, "height": 64, "fps": "24"}
    assert (
        hw.probe_encode(state, "hevc_nvenc", 31, target, cache_dir=tmp_path)["status"] == "verified"
    )
    assert hw.probe_encode(state, "hevc_nvenc", 31, target, cache_dir=tmp_path)["cached"]
    state["driver_queries"]["nvidia"]["devices"][0]["codecs"]["hevc"]["formats"]["yuv420p"] = False
    assert (
        hw.probe_encode(state, "hevc_nvenc", 31, target, cache_dir=tmp_path)["status"]
        == "unsupported"
    )
    assert len(calls) == 1
