import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from archivebench.archive import archive, candidates, cleanup, safe
from archivebench.core import benchmark, digest, fingerprint, run, save, validate_config, score
from archivebench.encoders import discover, options
from archivebench.report import public_result, write_report


def test_encoder_controls_and_discovery():
    supported, other = discover(
        " V....D libx265 encoder\n V..... hevc_nvenc NVIDIA\n V..... av1_unknown custom"
    )
    assert supported == ["hevc_nvenc", "libx265"]
    assert other == ["av1_unknown"]
    assert "lp=3" in options("libsvtav1", 35, "yuv420p10le")
    with pytest.raises(ValueError):
        options("libsvtav1", 100, "yuv420p10le")


def test_fingerprint_binds_parameters():
    assert fingerprint({"start": 0, "quality": 24}) != fingerprint({"start": 1, "quality": 24})


def test_scan_and_boundaries(tmp_path):
    (tmp_path / "original.mov").touch()
    (tmp_path / "generated.archive.mkv").touch()
    for directory in ("Proxy", "Proxies", "Archived Footage", ".git"):
        (tmp_path / directory).mkdir()
        (tmp_path / directory / "excluded.mov").touch()
    assert len(candidates(tmp_path)) == 1
    with pytest.raises(ValueError):
        safe(tmp_path.parent / "outside.mov", tmp_path)


def test_validation_rejects_bad_config():
    with pytest.raises(ValueError):
        validate_config({"version": 1, "mode": "quick", "profile": "compact", "samples": []})


@pytest.mark.parametrize("repeats", [0, -1, True, False, 1.5, "2", None])
def test_validation_rejects_invalid_encode_repeats(repeats):
    with pytest.raises(ValueError, match="encode_repeats must be a positive integer"):
        validate_config(
            {"version": 1, "mode": "thorough", "profile": "compact", "encode_repeats": repeats}
        )


def test_unsupported_source_formats(monkeypatch):
    import archivebench.core as core

    info = {
        "streams": [
            {
                "codec_type": "video",
                "avg_frame_rate": "30/1",
                "r_frame_rate": "30/1",
                "field_order": "progressive",
                "color_transfer": "smpte2084",
            }
        ],
        "format": {"duration": "2"},
    }
    monkeypatch.setattr(core, "probe", lambda *args: info)
    with pytest.raises(ValueError, match="HDR"):
        core.inspect_source(Path("fixture.mov"), 0, 1, "ffprobe")
    info["streams"][0]["color_transfer"] = "bt709"
    info["streams"][0]["field_order"] = "tt"
    with pytest.raises(ValueError, match="Interlaced"):
        core.inspect_source(Path("fixture.mov"), 0, 1, "ffprobe")
    info["streams"][0]["field_order"] = "progressive"
    info["streams"][0]["avg_frame_rate"] = "29/1"
    with pytest.raises(ValueError, match="Variable"):
        core.inspect_source(Path("fixture.mov"), 0, 1, "ffprobe")


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg integration test")
def test_real_benchmark_resume_report_and_archive(tmp_path):
    source_root = tmp_path / "originals"
    source_root.mkdir()
    source = source_root / "synthetic.mov"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=320x180:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-t",
            "2",
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-map",
            "1:a",
            "-map",
            "1:a",
            "-map",
            "1:a",
            "-c:v",
            "libx264",
            "-crf",
            "0",
            "-pix_fmt",
            "yuv422p10le",
            "-c:a",
            "pcm_s24le",
            "-color_range",
            "pc",
            "-colorspace",
            "bt709",
            "-color_trc",
            "bt709",
            "-color_primaries",
            "bt709",
            str(source),
        ]
    )
    original_hash = digest(source)
    config: dict[str, Any] = {
        "version": 1,
        "profile": "compact",
        "mode": "quick",
        "pixel_format": "yuv420p10le",
        "target_vmaf": 90,
        "budget_minutes": 3,
        "samples": [{"path": str(source), "label": "Synthetic motion", "start": 0, "seconds": 1}],
        "encoders": ["libx265", "libsvtav1"],
    }
    config_path = tmp_path / "config.json"
    save(config_path, config)
    result = benchmark(config_path, tmp_path / "bench")
    assert result["trials"], result["skipped"]
    assert {row["encoder"] for row in result["trials"]} == {"libx265", "libsvtav1"}, result[
        "skipped"
    ]
    assert digest(source) == original_hash
    sample = result["samples"][0]
    calibration_dir = tmp_path / "calibration"
    calibration_dir.mkdir()
    reference = tmp_path / "bench" / "sample-1" / "reference.mkv"
    calibrated = score(
        "ffmpeg", reference, reference, sample["video"], "yuv420p10le", calibration_dir, 1, 60
    )
    assert calibrated["vmaf"] >= 99.9 and calibrated["ssim"] == 1
    assert len(calibrated["vmaf_frames"]) == sample["video"]["frames"]
    assert calibrated["vmaf_frames"][0]["seconds"] == 0
    assert calibrated["vmaf_frames"][1]["seconds"] == pytest.approx(1 / 30)
    assert sum(frame["vmaf"] for frame in calibrated["vmaf_frames"]) / len(
        calibrated["vmaf_frames"]
    ) == pytest.approx(calibrated["vmaf"], abs=0.00001)
    frames = result["trials"][0]["vmaf_frames"]
    assert frames[1]["seconds"] == pytest.approx(2 / 30)
    assert len(benchmark(config_path, tmp_path / "bench")["trials"]) == len(result["trials"])
    config["samples"] = [
        {"path": str(source), "label": "Synthetic motion", "start": 0.1, "seconds": 1}
    ]
    save(config_path, config)
    with pytest.raises(ValueError, match="changed"):
        benchmark(config_path, tmp_path / "bench")
    report = write_report(result, tmp_path / "bench")
    assert "__RESULTS__" not in report.read_text(encoding="utf-8")
    assert '<script src="http' not in report.read_text(encoding="utf-8")
    assert str(source) not in json.dumps(public_result(result))
    assert public_result(result)["config"]["samples"][0]["path"] == "[local source]"
    assert all("output" not in row for row in public_result(result)["screening"])
    result["config"]["samples"][0]["label"] = "</script><script>alert(1)</script>"
    escaped = write_report(result, tmp_path / "bench").read_text(encoding="utf-8")
    assert "</script><script>alert(1)</script>" not in escaped
    settings = {
        "version": 1,
        "type": "archive-settings",
        "encoder": "libsvtav1",
        "quality": 35,
        "pixel_format": "yuv420p10le",
        "minimum_saving": 0.1,
        "drop_audio_tracks": [3, 4],
        "audio_kbps_per_channel": 192,
    }
    settings_path = tmp_path / "archive-settings.json"
    modern = {
        **settings,
        "version": 2,
        "encoder": "libx264",
        "quality": 23,
        "pixel_format": "source",
        "audio_mode": "aac",
        "audio_kbps_per_channel": 96,
        "drop_audio_tracks": [],
    }
    save(settings_path, modern)
    archive(source_root, tmp_path / "modern", settings_path, True)
    modern_manifest = json.loads(
        (tmp_path / "modern/archive-manifest.json").read_text(encoding="utf-8")
    )
    assert modern_manifest["records"][0]["status"] == "verified"
    assert digest(source) == original_hash
    save(settings_path, settings)
    archived = tmp_path / "archive"
    archive(source_root, archived, settings_path, False)
    assert not archived.exists()
    archive(source_root, archived, settings_path, True)
    manifest = json.loads((archived / "archive-manifest.json").read_text())
    assert manifest["records"][0]["status"] == "verified"
    archive(source_root, archived, settings_path, True)
    cleanup(archived, False, False)
    assert source.exists()
    with pytest.raises(ValueError, match="reviewed"):
        cleanup(archived, True, False)
    encoded = Path(manifest["records"][0]["output"])
    backup = encoded.read_bytes()
    encoded.write_bytes(b"tampered")
    with pytest.raises(ValueError):
        cleanup(archived, True, True)
    assert source.exists()
    encoded.write_bytes(backup)
    cleanup(archived, True, True)
    assert not source.exists() and encoded.exists()
