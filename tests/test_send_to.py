import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

WINDOWS = Path(__file__).parents[1] / "archivebench" / "windows"
pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows Send to")


def powershell(script, *args, input=""):
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-File", str(script), *map(str, args)],
        input=input,
        text=True,
        capture_output=True,
        timeout=90,
    )


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg required")
def test_launcher_preset_selection_archive_resume_and_changed_snapshot(tmp_path):
    source = tmp_path / "Footage & %literal%"
    source.mkdir()
    clip = source / "clip.mkv"
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:rate=10",
            "-t",
            "2",
            "-c:v",
            "ffv1",
            str(clip),
        ],
        check=True,
    )
    before = hashlib.sha256(clip.read_bytes()).hexdigest()
    presets = tmp_path / "Preset library"
    presets.mkdir()
    preset = presets / "smaller.json"
    settings = {
        "version": 2,
        "type": "archive-settings",
        "encoder": "libx264",
        "quality": 30,
        "pixel_format": "source",
        "resolution": "original",
        "minimum_saving": 0.1,
    }
    preset.write_text(json.dumps(settings))
    script = WINDOWS / "archivebench-send-to.ps1"
    cancelled = powershell(script, source, "-PresetDirectory", presets, "-NoPause", input="\n")
    assert cancelled.returncode == 0, cancelled.stderr
    output = Path(str(source) + "-Archived-smaller")
    job = Path(str(output) + ".job.json")
    assert not job.exists()
    first = powershell(
        script, source, "-PresetDirectory", presets, "-NoPause", input="1\nARCHIVE\n"
    )
    assert first.returncode == 0, first.stderr
    manifest = json.loads((output / "archive-manifest.json").read_text())
    assert manifest["records"][0]["status"] == "verified"
    archived = Path(manifest["records"][0]["output"])
    output_time = archived.stat().st_mtime_ns
    repeat = powershell(script, source, "-Preset", preset, "-NoPause", input="ARCHIVE\n")
    assert repeat.returncode == 0, repeat.stderr
    assert archived.stat().st_mtime_ns == output_time
    assert hashlib.sha256(clip.read_bytes()).hexdigest() == before
    assert "cleanup" not in first.stdout.lower() or "separate cleanup" in first.stdout.lower()
    original_job = job.read_bytes()
    preset.write_text(json.dumps({**settings, "quality": 28}))
    changed = powershell(script, source, "-Preset", preset, "-InspectOnly")
    assert changed.returncode != 0 and "different folders or settings" in changed.stderr
    assert job.read_bytes() == original_job


def test_installer_uses_durable_shortcut_and_rejects_multiple_sources(tmp_path):
    install = tmp_path / "Installed launcher"
    sendto = tmp_path / "Send to"
    presets = tmp_path / "Presets & %literal%"
    result = powershell(
        WINDOWS / "install-send-to.ps1",
        "-InstallDirectory",
        install,
        "-SendToDirectory",
        sendto,
        "-PresetDirectory",
        presets,
    )
    assert result.returncode == 0, result.stderr
    assert (install / "archivebench-send-to.ps1").read_bytes() == (
        WINDOWS / "archivebench-send-to.ps1"
    ).read_bytes()
    assert (sendto / "ArchiveBench.lnk").is_file()
    # Read the real shortcut through Windows COM without launching a UI.
    command = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:ARCHIVEBENCH_TEST_SHORTCUT); $s.Arguments"
    inspection = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        env={**os.environ, "ARCHIVEBENCH_TEST_SHORTCUT": str(sendto / "ArchiveBench.lnk")},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert inspection.returncode == 0, inspection.stderr
    assert str(install / "archivebench-send-to.ps1") in inspection.stdout
    assert str(presets) in inspection.stdout
    rejected = powershell(install / "archivebench-send-to.ps1", tmp_path, presets, "-InspectOnly")
    assert rejected.returncode != 0 and "exactly one" in rejected.stderr
