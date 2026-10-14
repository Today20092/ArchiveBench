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
