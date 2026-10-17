import json
import subprocess
import time
from copy import deepcopy

import pytest

from archivebench import hardware as hw
from archivebench.budget import deadline


@pytest.fixture
def machine():
    return {
        "configured": ["hevc_nvenc", "libx264"],
        "devices": [{"name": "GPU", "driver": "1"}],
        "inventory_errors": [],
        "tools": {
            "ffmpeg": {"path": "ffmpeg", "sha256": "a"},
            "ffprobe": {"path": "ffprobe", "sha256": "b"},
        },
    }


@pytest.fixture
def target():
    return {"width": 1920, "height": 1080, "pix_fmt": "yuv422p10le", "fps": "30000/1001"}


def successful_probe(monkeypatch, target, calls):
    monkeypatch.setattr(hw.core, "run", lambda args, *a: calls.append(args) or "")
    monkeypatch.setattr(
        hw.core,
        "probe",
        lambda *a: {
            "streams": [
                {
                    **target,
                    "codec_type": "video",
                    "codec_name": "hevc",
                    "avg_frame_rate": target["fps"],
                }
            ]
        },
    )


def test_exact_controls_output_and_cache_identity(tmp_path, monkeypatch, machine, target):
    calls = []
    successful_probe(monkeypatch, target, calls)

    def check(m=machine, t=target, q=31, refresh=False):
        return hw.probe_encode(m, "hevc_nvenc", q, t, cache_dir=tmp_path, refresh=refresh)

    assert check()["status"] == "verified"
    assert "yuv422p10le" in calls[0]
    assert "color=size=1920x1080:rate=30000/1001,format=yuv422p10le" in calls[0]
    assert calls[0][calls[0].index("-frames:v") + 1] == "3"
    assert check()["cached"] and len(calls) == 1
    changed = deepcopy(machine)
    changed["devices"][0]["driver"] = "2"
    assert not check(changed)["cached"]
    changed["tools"]["ffmpeg"]["sha256"] = "changed"
    assert not check(changed)["cached"]
    assert not check(q=30)["cached"]
    assert not check(refresh=True)["cached"]
    assert len(calls) == 5


@pytest.mark.parametrize(
    "field,value",
    [("pix_fmt", "yuv420p10le"), ("width", 1280), ("codec_name", "h264"), ("avg_frame_rate", "25")],
)
def test_silent_conversion_cannot_pass(tmp_path, monkeypatch, machine, target, field, value):
    monkeypatch.setattr(hw.core, "run", lambda *a: "")
    actual = {
        **target,
        "codec_type": "video",
        "codec_name": "hevc",
        "avg_frame_rate": target["fps"],
        field: value,
    }
    monkeypatch.setattr(hw.core, "probe", lambda *a: {"streams": [actual]})
    row = hw.probe_encode(machine, "hevc_nvenc", 31, target, cache_dir=tmp_path)
    assert row["status"] == "unsupported"
    assert "differs" in row["reason"]


@pytest.mark.parametrize(
    "error,status",
    [
        (RuntimeError("YUV422P not supported"), "unsupported"),
        (RuntimeError("out of memory; No capable devices found"), "probe-failed"),
        (RuntimeError("driver API mismatch"), "probe-failed"),
        (subprocess.TimeoutExpired("ffmpeg", 1), "probe-failed"),
    ],
)
def test_errors_and_retryable_failures(tmp_path, monkeypatch, machine, target, error, status):
    calls = []

    def fail(*args):
        calls.append(args)
        raise error

    monkeypatch.setattr(hw.core, "run", fail)
    for _ in range(2):
        assert (
            hw.probe_encode(machine, "hevc_nvenc", 31, target, cache_dir=tmp_path)["status"]
            == status
        )
    assert len(calls) == (1 if status == "unsupported" else 2)


def test_missing_adapter_does_not_encode(tmp_path, monkeypatch, machine, target):
    machine["configured"] = []
    monkeypatch.setattr(hw.core, "run", lambda *a: pytest.fail("should not encode"))
    assert (
        hw.probe_encode(machine, "hevc_nvenc", 31, target, cache_dir=tmp_path)["status"]
        == "unsupported"
    )


def test_expired_corrupt_and_unidentified_cache(tmp_path, monkeypatch, machine, target):
    calls = []
    successful_probe(monkeypatch, target, calls)

    def check():
        return hw.probe_encode(machine, "hevc_nvenc", 31, target, cache_dir=tmp_path)

    check()
    path = next(tmp_path.glob("*.json"))
    saved = json.loads(path.read_text())
    saved["observed_at"] = time.time() - hw.CACHE_SECONDS - 1
    path.write_text(json.dumps(saved))
    assert not check()["cached"]
    path.write_text("partial")
    assert not check()["cached"]
    machine["devices"] = []
    assert not check()["cached"] and not check()["cached"]
    assert len(calls) == 5


def test_config_checks_mixed_formats_and_filters_only_verified(monkeypatch, machine):
    monkeypatch.setattr(hw, "inventory", lambda *a: machine)
    monkeypatch.setattr(
        hw.core,
        "probe",
        lambda path, *a: {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "avg_frame_rate": "30",
                    "pix_fmt": "yuv422p10le" if str(path) == "422" else "yuv420p",
                }
            ]
        },
    )
    calls = []

    def check(h, e, q, t, **kw):
        calls.append(t["pix_fmt"])
        return {
            "encoder": e,
            "quality": q,
            "status": "verified" if e == "libx264" or t["pix_fmt"] == "yuv420p" else "unsupported",
        }

    monkeypatch.setattr(hw, "probe_encode", check)
    config = {
        "strategy": "fixed",
        "pixel_format": "source",
        "samples": [{"path": "422"}, {"path": "420"}, {"path": "420"}],
        "encoders": ["libx264", "hevc_nvenc"],
        "fixed_settings": {"libx264": [23], "hevc_nvenc": [31]},
    }
    result = hw.check_config(config)
    assert len(calls) == 4 and len(result["checks"]) == 6
    assert result["verified_encoders"] == ["libx264"]
    assert hw.suggested_encoders(result) == ["libx264"]
    assert config["pixel_format"] == "source" and config["encoders"] == ["libx264", "hevc_nvenc"]


def test_deadline_unknown_not_unsupported(monkeypatch):
    monkeypatch.setattr(
        hw, "inventory", lambda *a: (_ for _ in ()).throw(subprocess.TimeoutExpired("inventory", 0))
    )
    prior = deadline.get()
    result = hw.availability({})
    assert result["status"] == "unknown" and result["verified_encoders"] == []
    assert deadline.get() == prior


def test_capability_details_do_not_leak_into_portable_report():
    from archivebench.report import public_result

    result = {
        "config": {"samples": []},
        "trials": [],
        "skipped": [],
        "capabilities": {
            "hardware": {"devices": [{"uuid": "private-device"}]},
            "checks": [{"source": "C:/private/clip.mov"}],
        },
    }
    public = public_result(result)
    assert "capabilities" not in public
    assert "capabilities" in result


def test_doctor_config_refresh_routes_to_shared_checks(tmp_path, monkeypatch, capsys):
    from archivebench import cli

    config = {"samples": [], "encoders": ["libx264"]}
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setattr(cli, "validate_config", lambda value: None)
    calls = []

    def check(value, **kwargs):
        calls.append((value, kwargs))
        return {"status": "unknown", "checks": []}

    monkeypatch.setattr(cli, "availability", check)
    monkeypatch.setattr("sys.argv", ["archivebench", "doctor", "--config", str(path), "--refresh"])
    cli.main()
    assert calls == [(config, {"refresh": True})]
    assert json.loads(capsys.readouterr().out)["status"] == "unknown"


def test_inventory_distinguishes_compiled_encoders_from_devices(monkeypatch):
    monkeypatch.setattr(hw.shutil, "which", lambda name: None if name == "nvidia-smi" else name)
    monkeypatch.setattr(hw.core, "digest", lambda path: "binary")

    def run(args, *rest):
        if "-encoders" in args:
            return " V..... libx264 library\n V..... hevc_nvenc compiled but no device\n"
        if "-filters" in args:
            return "libvmaf"
        if args[0] == "powershell":
            return "[]"
        return "tool version"

    monkeypatch.setattr(hw.core, "run", run)
    found = hw.inventory()
    assert found["devices"] == []
    assert found["configured"] == ["hevc_nvenc", "libx264"]
    assert found["decode"]["hardware_support"] == "not-probed"
    assert "verified_encoders" not in found
