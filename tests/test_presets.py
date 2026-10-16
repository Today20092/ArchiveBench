import json
import sys
import shutil

import pytest

from archivebench.cli import main
from archivebench.presets import inspect_preset, make_preset, resolve_settings
from archivebench.archive import archive
from archivebench.core import run


SETTINGS = {
    "version": 2,
    "type": "archive-settings",
    "encoder": "libx265",
    "quality": 24,
    "pixel_format": "source",
    "resolution": "original",
}


def test_starter_presets_export_without_benchmark(tmp_path, monkeypatch, capsys):
    from archivebench.presets import starter_paths

    paths = starter_paths()
    documents = [json.loads(path.read_text()) for path in paths]
    assert [preset["name"] for preset in documents] == [
        "Quality priority",
        "Balanced",
        "Space priority",
        "Balanced (AVC alternative)",
    ]
    assert [resolve_settings(preset)["quality"] for preset in documents] == [20, 24, 28, 23]
    for index, (path, preset) in enumerate(zip(paths, documents)):
        settings = resolve_settings(preset)
        assert settings["pixel_format"] == "source"
        assert settings["resolution"] == "original"
        assert settings["audio_mode"] == "copy"
        assert preset["scope"]["footage"] == []
        assert preset["evidence"]["measurement_status"] == "unmeasured-starter"
        assert preset["evidence"]["estimates"]["basis"] == "unknown"
        assert preset["evidence"]["visual_status"] == "unreviewed"
        output = tmp_path / f"export-{index}.json"
        monkeypatch.setattr(
            sys, "argv", ["archivebench", "preset", "export", str(path), "--output", str(output)]
        )
        main()
        assert json.loads(output.read_text()) == preset
    monkeypatch.setattr(sys, "argv", ["archivebench", "preset", "list"])
    main()
    assert "Quality priority" in capsys.readouterr().out


def test_preset_scope_is_not_current_project_validation():
    preset = make_preset(SETTINGS)
    preset["scope"]["footage"] = [{"pixel_format": "yuv422p10le"}]
    report = inspect_preset(
        preset,
        {
            "supported_encoders": ["hevc_nvenc"],
            "footage": [{"pixel_format": "yuv420p"}],
            "skip_sample_check": True,
        },
    )
    assert report["unsupported"] == ["encoder/hardware unavailable"]
    assert report["footage_scope"] == "untested"
    assert report["current_project_validated"] is False
    preset["settings"]["quality"] = 25
    with pytest.raises(ValueError, match="options|evidence"):
        resolve_settings(preset)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_one_preset_archives_two_folder_roots_without_mutation(tmp_path):
    settings = {
        **SETTINGS,
        "encoder": "libx264",
        "quality": 30,
        "pixel_format": "yuv420p",
        "metadata": "drop",
    }
    preset = make_preset(settings)
    path = tmp_path / "preset.json"
    path.write_text(json.dumps(preset))
    before = path.read_bytes()
    for name in ("project-a", "project-b"):
        root = tmp_path / name
        root.mkdir()
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=red:size=64x48:rate=24",
                "-t",
                "0.5",
                "-c:v",
                "libx264",
                "-crf",
                "0",
                str(root / "clip.mp4"),
            ]
        )
        archive(root, tmp_path / (name + "-archive"), path, False)
    assert path.read_bytes() == before


def test_malformed_preset_quality_is_rejected():
    invalid = {**SETTINGS, "quality": True}
    with pytest.raises(ValueError, match="integer"):
        make_preset(invalid)


def test_source_matching_preset_rejects_unavailable_source_format():
    preset = make_preset(SETTINGS)
    report = inspect_preset(
        preset,
        {
            "supported_encoders": ["libx265"],
            "supported_pixel_formats": ["yuv420p", "yuv420p10le"],
            "footage": [{"pix_fmt": "yuv422p10le"}],
        },
    )
    assert report["compatibility"] == "unsupported"
    assert report["unsupported"] == ["output pixel format unavailable"]
    assert resolve_settings(preset) == SETTINGS


def test_cli_imports_legacy_settings_as_portable_preset(tmp_path, monkeypatch, capsys):
    source = tmp_path / "settings.json"
    source.write_text(
        json.dumps(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx265",
                "quality": 24,
                "pixel_format": "source",
                "resolution": "original",
            }
        )
    )
    output = tmp_path / "preset.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "archivebench",
            "preset",
            "import",
            str(source),
            "--output",
            str(output),
            "--name",
            "HEVC CPU",
        ],
    )
    main()
    preset = json.loads(output.read_text())
    assert preset["type"] == "archive-preset"
    assert preset["settings"]["quality"] == 24
    assert preset["evidence"]["measurement_status"] == "unknown"
    monkeypatch.setattr(sys, "argv", ["archivebench", "preset", "inspect", str(output)])
    main()
    assert "current_project_validated" in capsys.readouterr().out
