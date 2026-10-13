import json
import shutil
from pathlib import Path
from typing import Any

import pytest

from archivebench.archive import (
    archive,
    cleanup,
    verify_archive,
    verify_retention,
    validate_settings,
)
from archivebench.core import benchmark, digest, primary, probe, run, save
from archivebench.encoders import options
from archivebench.formats import output_video, retention, scale_filter, validate_formats


def test_output_choices_and_validation():
    video = {"width": 3840, "height": 2160, "pix_fmt": "yuv422p10le"}
    assert output_video(video, {"pixel_format": "source"}) == video
    scaled = output_video(video, {"pixel_format": "yuv420p", "resolution": "1080p"})
    assert scaled == {"width": 1920, "height": 1080, "pix_fmt": "yuv420p"}
    assert scale_filter(video, scaled) == "scale=1920:1080:flags=lanczos"
    portrait = output_video(
        {**video, "width": 2160, "height": 3840}, {"pixel_format": "source", "resolution": "720p"}
    )
    assert (portrait["width"], portrait["height"]) == (720, 1280)
    small = {**video, "width": 640, "height": 360}
    assert output_video(small, {"pixel_format": "source", "resolution": "1080p"}) == small
    with pytest.raises(ValueError, match="unsupported"):
        output_video({**video, "pix_fmt": "gbrp"}, {"pixel_format": "source"})
    args = options("hevc_vaapi", 25, "yuv420p10le", scale_filter(video, scaled))
    assert args.count("-vf") == 1 and "scale=1920:1080:flags=lanczos,format=p010le,hwupload" in args
    for key, value in [
        ("resolution", "1080"),
        ("audio_mode", "bad"),
        ("drop_audio_tracks", [0]),
        ("drop_audio_tracks", [1, 1]),
        ("drop_audio_tracks", [True]),
        ("audio_kbps_per_channel", 0),
        ("subtitles", "ignore"),
    ]:
        with pytest.raises(ValueError):
            validate_formats({"pixel_format": "source", key: value})
    assert retention({})["drop_audio_tracks"] == []
    assert retention({"type": "archive-settings", "version": 1})["drop_audio_tracks"] == [3, 4]


def test_metadata_and_attachment_loss_blocks_verification():
    import copy

    original: dict[str, Any] = {
        "streams": [{"codec_type": "video"}],
        "format": {"tags": {"title": "Keep me"}},
        "chapters": [{"start_time": "0", "end_time": "1", "tags": {"title": "Intro"}}],
    }
    encoded = copy.deepcopy(original)
    encoded["format"]["tags"] = {}
    with pytest.raises(ValueError, match="metadata"):
        verify_retention(original, encoded, Path("source"), Path("output"), retention({}), "ffmpeg")
    encoded = copy.deepcopy(original)
    encoded["chapters"][0]["end_time"] = "0.5"
    with pytest.raises(ValueError, match="chapter timing"):
        verify_retention(original, encoded, Path("source"), Path("output"), retention({}), "ffmpeg")
    original["streams"].append({"codec_type": "attachment", "extradata_hash": "SHA256:original"})
    encoded = copy.deepcopy(original)
    encoded["streams"][-1]["extradata_hash"] = "SHA256:changed"
    with pytest.raises(ValueError, match="attachment content"):
        verify_retention(original, encoded, Path("source"), Path("output"), retention({}), "ffmpeg")


def test_wizard_saves_retention_and_video_choices(tmp_path, monkeypatch, capsys):
    import archivebench.cli as cli

    source = tmp_path / "source.mov"
    source.touch()
    monkeypatch.setattr(
        cli,
        "probe",
        lambda _: {
            "format": {"duration": "30"},
            "streams": [
                {"codec_type": "video", "width": 3840, "height": 2160, "pix_fmt": "yuv422p10le"}
            ],
        },
    )
    answers = iter(
        [
            str(source),
            "1",
            "",
            "",
            "yuv420p10le",
            "1080p",
            "aac",
            "3,4",
            "128",
            "copy",
            "drop",
            "copy",
            "2",
            "0",
        ]
    )
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    config_path = tmp_path / "config.json"
    cli.wizard(config_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert config["pixel_format"] == "yuv420p10le" and config["resolution"] == "1080p"
    assert retention(config) == {
        "audio_mode": "aac",
        "drop_audio_tracks": [3, 4],
        "audio_kbps_per_channel": 128,
        "subtitles": "copy",
        "attachments": "drop",
        "metadata": "copy",
    }
    assert "3840x2160 yuv422p10le -> 1920x1080 yuv420p10le" in capsys.readouterr().out


@pytest.fixture
def media_source(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg integration test")
    root = tmp_path / "sources"
    root.mkdir()
    subtitle = tmp_path / "captions.srt"
    subtitle.write_text(
        "1\n00:00:00,000 --> 00:00:01,800\nRetain this caption.\n", encoding="utf-8"
    )
    attachment = tmp_path / "notes.txt"
    attachment.write_text("Retain this attachment.", encoding="utf-8")
    metadata = tmp_path / "chapters.txt"
    metadata.write_text(
        ";FFMETADATA1\ntitle=Archive test\n[CHAPTER]\nTIMEBASE=1/1000\nSTART=0\nEND=1800\ntitle=Opening\n",
        encoding="utf-8",
    )
    source = root / "source.mkv"
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
            "testsrc2=size=1440x810:rate=12",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=48000",
            "-i",
            str(subtitle),
            "-f",
            "ffmetadata",
            "-i",
            str(metadata),
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
            "-map",
            "2:s",
            "-map_metadata",
            "3",
            "-map_chapters",
            "3",
            "-metadata:s:a:0",
            "language=eng",
            "-metadata:s:a:1",
            "title=Second microphone",
            "-c:v",
            "ffv1",
            "-pix_fmt",
            "yuv422p10le",
            "-c:a",
            "pcm_s16le",
            "-c:s",
            "srt",
            "-attach",
            str(attachment),
            "-metadata:s:t:0",
            "mimetype=text/plain",
            str(source),
        ]
    )
    return root, source


def test_scaled_benchmark_against_original(media_source, tmp_path):
    _, source = media_source
    config = {
        "version": 1,
        "profile": "compact",
        "mode": "quick",
        "pixel_format": "source",
        "resolution": "720p",
        "target_vmaf": 90,
        "budget_minutes": 3,
        "samples": [{"path": str(source), "start": 0, "seconds": 1}],
        "encoders": ["libx264"],
    }
    settings = tmp_path / "config.json"
    save(settings, config)
    result = benchmark(settings, tmp_path / "bench")
    assert result["trials"], result["skipped"]
    trial = result["trials"][0]
    assert (trial["width"], trial["height"], trial["pixel_format"]) == (1280, 720, "yuv422p10le")
    reference = primary(probe(tmp_path / "bench/sample-1/reference.mkv"))
    assert (reference["width"], reference["height"]) == (1440, 810)
    assert 0 < trial["vmaf"] < 100 and trial["ssim"] < 1
    assert len(benchmark(settings, tmp_path / "bench")["trials"]) == len(result["trials"])
    config["resolution"] = "original"
    save(settings, config)
    with pytest.raises(ValueError, match="changed"):
        benchmark(settings, tmp_path / "bench")


@pytest.mark.parametrize("mode", ["copy", "aac", "none"])
def test_archive_retention_and_cleanup_checks(media_source, tmp_path, mode):
    root, source = media_source
    original_hash = digest(source)
    settings = {
        "version": 2,
        "type": "archive-settings",
        "encoder": "libx264",
        "quality": 23,
        "pixel_format": "source" if mode == "copy" else "yuv420p",
        "resolution": "720p",
        "audio_mode": mode,
        "drop_audio_tracks": [2] if mode == "aac" else [],
        "audio_kbps_per_channel": 128,
        "subtitles": "drop" if mode == "none" else "copy",
        "attachments": "drop" if mode == "none" else "copy",
        "metadata": "drop" if mode == "none" else "copy",
    }
    validate_settings(settings)
    settings_path = tmp_path / "settings.json"
    save(settings_path, settings)
    out = tmp_path / "archive"
    archive(root, out, settings_path, False)
    assert not out.exists()
    archive(root, out, settings_path, True)
    manifest = json.loads((out / "archive-manifest.json").read_text())
    assert manifest["records"][0]["status"] == "verified"
    encoded_path = Path(manifest["records"][0]["output"])
    encoded = probe(encoded_path)
    assert (primary(encoded)["width"], primary(encoded)["height"]) == (1280, 720)
    audio = [s for s in encoded["streams"] if s["codec_type"] == "audio"]
    assert len(audio) == {"copy": 4, "aac": 3, "none": 0}[mode]
    if mode == "copy":
        assert all(s["codec_name"] == "pcm_s16le" for s in audio)
    if mode == "aac":
        assert all(s["codec_name"] == "aac" for s in audio)
    if mode == "none":
        assert not encoded.get("chapters")
        assert not any(s["codec_type"] in ("subtitle", "attachment") for s in encoded["streams"])
        assert "title" not in encoded["format"].get("tags", {})
    else:
        assert len(encoded["chapters"]) == 1
        with pytest.raises(ValueError, match="selection"):
            verify_archive(
                encoded_path, source, {**settings, "audio_mode": "none"}, "ffmpeg", "ffprobe"
            )
    cleanup(out, False, False)
    assert digest(source) == original_hash
    # Exercise the complete deletion guard only on this synthetic fixture.
    cleanup(out, True, True)
    assert not source.exists() and encoded_path.exists()
