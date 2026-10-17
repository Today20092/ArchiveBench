"""Manufacturer facts must exclude impossible work without certifying unknown hardware."""

import importlib
import json
import shutil
import subprocess

import pytest

from archivebench import core, fixed, hardware as hw, jobs
from archivebench import hardware_limits as hardware


def snapshot(*names):
    return {
        "devices": [
            {"name": name, "index": str(index), "vendor": "NVIDIA"}
            for index, name in enumerate(names)
        ],
        "table_revision": hardware.REVISION,
        "manufacturer_sources": [hardware.MATRIX, hardware.SDK],
        "visibility": {},
        "platform": "test",
        "cpu": "Test CPU",
        "logical_cpus": 4,
        "inventory_errors": [],
        "tools": {
            "ffmpeg": {"path": shutil.which("ffmpeg") or "ffmpeg"},
            "ffprobe": {"path": shutil.which("ffprobe") or "ffprobe"},
        },
        "configured": list(hardware.SPECS),
        "encoder_pixel_formats": {},
    }


@pytest.mark.parametrize(
    "name,codec,pixel,expected",
    [
        ("NVIDIA GeForce RTX 3070 Ti", "hevc", "yuv422p10le", False),
        ("NVIDIA GeForce RTX 3070 Ti", "hevc", "yuv420p10le", True),
        ("GeForce RTX 3070 Ti", "av1", "yuv420p", False),
        ("GeForce RTX 3070 Ti Laptop GPU", "h264", "yuv420p10le", False),
        ("GeForce RTX 2080 Ti", "hevc", "yuv422p", False),
        ("GeForce RTX 4070 Ti SUPER", "av1", "yuv420p10le", True),
        ("GeForce RTX 4090", "hevc", "yuv422p10le", False),
        ("GeForce RTX 5090", "hevc", "yuv422p10le", True),
        ("GeForce RTX 5070 Laptop GPU", "h264", "yuv422p10le", True),
        ("GeForce RTX 5090", "av1", "yuv422p10le", False),
        ("GeForce RTX 6090", "hevc", "yuv422p10le", None),
        ("NVIDIA RTX A4000", "hevc", "yuv422p10le", None),
        ("GeForce GTX 1650", "hevc", "yuv422p10le", None),
    ],
)
def test_nvidia_manufacturer_limits(name, codec, pixel, expected):
    assert hardware.manufacturer_support(name, codec, pixel) is expected


@pytest.mark.parametrize(
    "name,codec,pixel,expected",
    [
        ("AMD Radeon RX 6500 XT", "h264", "yuv420p", False),
        ("AMD Radeon RX 6400", "hevc", "yuv420p", False),
        ("AMD Radeon RX 5700 XT", "av1", "yuv420p", False),
        ("AMD Radeon RX 6800 XT", "av1", "yuv420p", False),
        ("AMD Radeon RX 7900 XTX", "av1", "yuv420p10le", True),
        ("AMD Radeon RX 9070 XT", "av1", "yuv420p10le", True),
        ("AMD Radeon RX 9070 XT", "hevc", "yuv422p10le", False),
        ("AMD Radeon RX 7900 XTX", "h264", "yuv420p10le", False),
        ("AMD Radeon RX 6800 XT", "hevc", "yuv420p10le", True),
        ("AMD Radeon Graphics", "av1", "yuv420p", None),
        ("AMD Radeon RX 9900 XT", "av1", "yuv420p", None),
    ],
)
def test_amd_manufacturer_limits(name, codec, pixel, expected):
    assert hardware.amd_support(name, codec, pixel) is expected


def test_intersection_and_unknown_devices():
    old = snapshot("GeForce RTX 3070 Ti")
    assert hardware.check_capability(old, "hevc_nvenc", "yuv422p10le")["status"] == "unsupported"
    assert hardware.check_capability(old, "hevc_nvenc", "yuv420p10le")["status"] == "candidate"
    new = snapshot("GeForce RTX 5090")
    new["encoder_pixel_formats"]["hevc_nvenc"] = ["nv12", "p010le", "cuda"]
    evidence = hardware.check_capability(new, "hevc_nvenc", "yuv422p10le")
    assert evidence["status"] == "unsupported" and "FFmpeg" in evidence["reason"]
    assert hardware.check_capability(new, "hevc_nvenc", "yuv420p10le")["status"] == "candidate"
    for state in (
        snapshot(),
        snapshot("Future GPU"),
        snapshot("GeForce RTX 3070 Ti", "Future GPU"),
        snapshot("GeForce RTX 3070 Ti", "GeForce RTX 5090"),
    ):
        assert hardware.check_capability(state, "hevc_nvenc", "yuv422p10le")["status"] == "unknown"
    old["visibility"] = {"CUDA_VISIBLE_DEVICES": "0"}
    assert hardware.check_capability(old, "hevc_nvenc", "yuv422p10le")["status"] == "unknown"


def test_amd_inventory_and_apple_unknown_chroma():
    state = snapshot()
    state["devices"] = [{"name": "AMD Radeon RX 7900 XTX"}]
    assert hardware.check_capability(state, "hevc_amf", "yuv422p10le")["status"] == "unsupported"
    assert hardware.check_capability(state, "av1_amf", "yuv420p10le")["status"] == "candidate"
    state["devices"].append({"name": "AMD Radeon Graphics"})
    assert hardware.check_capability(state, "hevc_amf", "yuv422p10le")["status"] == "unknown"
    state["apple_chip"] = "Apple M4 Pro"
    evidence = hardware.check_capability(state, "hevc_videotoolbox", "yuv422p10le")
    assert evidence["status"] == "unknown" and evidence["codec_support"]
    assert "Apple" in evidence["reason"]
    assert hardware.check_capability(state, "hevc_qsv", "yuv422p10le")["status"] == "unknown"


def test_pixel_layouts_and_missing_encoders():
    state = snapshot()
    state["encoder_pixel_formats"]["libx264"] = ["yuv420p", "nv12"]
    assert hardware.check_capability(state, "libx264", "yuv422p10le")["status"] == "unsupported"
    state["encoder_pixel_formats"]["hevc_qsv"] = ["qsv"]
    assert hardware.check_capability(state, "hevc_qsv", "yuv422p10le")["status"] == "unknown"
    state["configured"].remove("hevc_nvenc")
    with pytest.raises(ValueError, match="Not present"):
        hardware.require_capability(state, "hevc_nvenc", "yuv420p")


def test_local_device_evidence_is_not_exported():
    from archivebench.report import public_result

    state = snapshot("GeForce RTX 3070 Ti")
    state["devices"][0]["uuid"] = "private-device-identity"
    evidence = hardware.check_capability(state, "hevc_nvenc", "yuv422p10le")
    result = {
        "config": {"samples": []},
        "trials": [],
        "capabilities": {"hardware": state},
        "work": [{"reason": evidence["reason"], "capability": evidence}],
        "skipped": [{"reason": evidence["reason"], "capability": evidence}],
    }
    public = public_result(result)
    assert "private-device-identity" not in json.dumps(public)
    assert "capability" not in public["work"][0] and "capability" not in public["skipped"][0]
    assert result["skipped"][0]["capability"]["devices"][0]["uuid"] == "private-device-identity"


@pytest.mark.parametrize("system", ["Windows", "Darwin"])
def test_inventory_extends_existing_discovery(monkeypatch, system):
    monkeypatch.setattr(hw.platform, "system", lambda: system)
    monkeypatch.setattr(hw.platform, "processor", lambda: "")
    monkeypatch.setattr(hw.shutil, "which", lambda name: name)
    monkeypatch.setattr(hw.core, "digest", lambda path: "binary")

    def run(args, *rest):
        if args[0] == "nvidia-smi":
            return "0, GPU-id, NVIDIA GeForce RTX 3070 Ti, 0x248210DE, 610.62, 8192"
        if args[0] == "powershell":
            return (
                "Test CPU"
                if "Win32_Processor" in args[-1]
                else '[{"Name":"AMD Radeon RX 6500 XT","PNPDeviceID":"id","DriverVersion":"1"}]'
            )
        if args[0] == "sysctl":
            return "Apple M4 Pro"
        if args[0] == "system_profiler":
            return '{"SPDisplaysDataType":[{"sppci_model":"Apple M4 Pro","serial":"private"}]}'
        if "-encoders" in args:
            return " V..... hevc_nvenc encoder\n V..... h264_amf encoder\n V..... hevc_videotoolbox encoder"
        if "-filters" in args:
            return "libvmaf"
        if "-h" in args:
            return "Supported pixel formats: nv12 p010le nv16 p210le cuda"
        return "version"

    monkeypatch.setattr(hw.core, "run", run)
    state = hw.inventory()
    assert state["encoder_pixel_formats"]["hevc_nvenc"] == [
        "nv12",
        "p010le",
        "nv16",
        "p210le",
        "cuda",
    ]
    if system == "Windows":
        assert state["cpu"] == "Test CPU"
        assert hardware.check_capability(state, "h264_amf", "yuv420p")["status"] == "unsupported"
    else:
        assert state["apple_chip"] == "Apple M4 Pro"
        assert "private" not in json.dumps(state)
        assert (
            hardware.check_capability(state, "hevc_videotoolbox", "yuv422p10le")["status"]
            == "unknown"
        )


def test_unavailable_help_and_incomplete_inventory_stay_unknown(monkeypatch):
    state = snapshot("GeForce RTX 3070 Ti")
    state["inventory_errors"] = ["NVIDIA inventory unavailable: malformed data"]

    def fail(*args):
        raise subprocess.TimeoutExpired("help", 5)

    enriched = hardware.add_limits(state, fail)
    assert all(value is None for value in enriched["encoder_pixel_formats"].values())
    assert hardware.check_capability(enriched, "hevc_nvenc", "yuv422p10le")["status"] == "unknown"
    assert hardware.check_capability({}, "hevc_nvenc", "yuv422p10le")["status"] == "unknown"


@pytest.fixture
def synthetic_source(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg required")
    source = tmp_path / "source.mkv"
    core.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=4",
            "-t",
            "2",
            "-c:v",
            "ffv1",
            str(source),
        ]
    )
    return source


@pytest.mark.parametrize("strategy", ["fixed", "tune"])
def test_benchmarks_do_not_encode_impossible_formats(
    tmp_path, monkeypatch, synthetic_source, strategy
):
    state = snapshot("GeForce RTX 3070 Ti")
    monkeypatch.setattr(fixed if strategy == "fixed" else hw, "inventory", lambda *args: state)
    original_run = core.run

    def guarded_run(args, timeout=120):
        assert "-c:v" not in args, "Unsupported comparison must not encode or prepare references"
        return original_run(args, timeout)

    monkeypatch.setattr(core, "run", guarded_run)
    config = {
        "version": 1,
        "profile": "editing",
        "mode": "quick",
        "strategy": strategy,
        "budget_minutes": 1,
        "pixel_format": "yuv422p10le",
        "resolution": "original",
        "encoders": ["hevc_nvenc"],
        "fixed_settings": {"hevc_nvenc": [31]},
        "samples": [{"path": str(synthetic_source), "start": 0, "seconds": 1}],
    }
    path = tmp_path / "config.json"
    core.save(path, config)
    result = core.benchmark(path, tmp_path / "run")
    assert not result["trials"] and not result["screening"]
    assert any(
        row.get("capability", {}).get("status") == "unsupported" for row in result["skipped"]
    )
    assert result["capabilities"]["hardware"]["devices"] == state["devices"]
    original = (tmp_path / "run" / "results.json").read_bytes()
    state["devices"][0]["driver"] = "changed"
    with pytest.raises(ValueError, match="changed"):
        core.benchmark(path, tmp_path / "run")
    assert (tmp_path / "run" / "results.json").read_bytes() == original


def test_archive_preflight_retains_unsupported_source(tmp_path, monkeypatch, synthetic_source):
    state = snapshot("GeForce RTX 3070 Ti")
    monkeypatch.setattr(jobs, "inventory", lambda *args: state)
    original_run = jobs.run

    def guarded_run(args, timeout=120):
        assert "-c:v" not in args
        return original_run(args, timeout)

    monkeypatch.setattr(jobs, "run", guarded_run)
    settings = {
        "version": 2,
        "type": "archive-settings",
        "encoder": "hevc_nvenc",
        "quality": 31,
        "pixel_format": "yuv422p10le",
        "resolution": "original",
    }
    preset = tmp_path / "preset.json"
    core.save(preset, settings)
    plan = jobs.inspect_job(
        jobs.create_job(tmp_path, tmp_path / "outputs", preset), alternatives=[]
    )
    row = plan["files"][0]
    assert row["action"] == "keep-original" and row["capability"]["status"] == "unsupported"
    assert "Manufacturer" in row["gaps"][0]
    assert synthetic_source.is_file() and plan["hardware"]["devices"]


def test_archive_execution_rechecks_hardware(tmp_path, monkeypatch, synthetic_source):
    archive = importlib.import_module("archivebench.archive")
    state = snapshot("GeForce RTX 3070 Ti")
    monkeypatch.setattr(hw, "inventory", lambda *args: state)
    settings = {
        "version": 2,
        "type": "archive-settings",
        "encoder": "hevc_nvenc",
        "quality": 31,
        "pixel_format": "yuv422p10le",
        "resolution": "original",
    }
    preset = tmp_path / "preset.json"
    core.save(preset, settings)
    original = core.digest(synthetic_source)
    with pytest.raises(ValueError, match="Manufacturer"):
        archive.archive(tmp_path, tmp_path / "outputs", preset, True)
    assert core.digest(synthetic_source) == original
    manifest = json.loads((tmp_path / "outputs" / "archive-manifest.json").read_text())
    assert manifest["records"][0]["capability"]["status"] == "unsupported"
    assert not list((tmp_path / "outputs").glob("*.mkv"))
    assert not (tmp_path / "outputs" / ".lock").exists()
