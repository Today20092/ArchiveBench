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
    assert changed.returncode != 0
    assert "different folders or settings" in " ".join(changed.stderr.split())
    assert job.read_bytes() == original_job


def test_installer_uses_durable_shortcut_and_rejects_multiple_sources(tmp_path):
    install = tmp_path / "Installed launcher"
    sendto = tmp_path / "Send to"
    presets = tmp_path / "Presets & %literal%"
    sendto.mkdir()
    for old in ("ArchiveBench", "ArchiveBench Desktop", "ArchiveBench Cleanup"):
        (sendto / f"{old}.lnk").write_text("obsolete")
    result = powershell(
        WINDOWS / "install-send-to.ps1",
        "-Legacy",
        "-InstallDirectory",
        install,
        "-SendToDirectory",
        sendto,
        "-PresetDirectory",
        presets,
    )
    assert result.returncode == 0, result.stderr
    assert not list(sendto.glob("ArchiveBench*.lnk"))
    assert (install / "archivebench-send-to.ps1").read_bytes() == (
        WINDOWS / "archivebench-send-to.ps1"
    ).read_bytes()
    for name in ("Archive footage", "Archive footage (terminal)", "Review originals for deletion"):
        assert (sendto / f"{name}.lnk").is_file()
    # Read the real shortcut through Windows COM without launching a UI.
    command = "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:ARCHIVEBENCH_TEST_SHORTCUT); $s.TargetPath; $s.Arguments"
    inspection = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        env={
            **os.environ,
            "ARCHIVEBENCH_TEST_SHORTCUT": str(sendto / "Archive footage (terminal).lnk"),
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert inspection.returncode == 0, inspection.stderr
    assert str(install / "archivebench-send-to.ps1") in inspection.stdout
    assert str(presets) in inspection.stdout
    assert "-NoExit" in inspection.stdout
    assert "conhost.exe" in inspection.stdout
    assert "powershell.exe" in inspection.stdout
    rejected = powershell(install / "archivebench-send-to.ps1", tmp_path, presets, "-InspectOnly")
    assert rejected.returncode != 0 and "exactly one" in rejected.stderr


@pytest.mark.parametrize("script", ["archivebench-send-to.ps1", "archivebench-desktop.ps1"])
def test_interactive_errors_do_not_terminate_powershell(script):
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "& $env:ARCHIVEBENCH_TEST_SCRIPT; Write-Output 'HOST_STILL_OPEN'",
        ],
        env={**os.environ, "ARCHIVEBENCH_TEST_SCRIPT": str(WINDOWS / script)},
        input="\n",
        text=True,
        capture_output=True,
        timeout=15,
    )
    assert "exactly one" in result.stderr
    assert "HOST_STILL_OPEN" in result.stdout


@pytest.mark.parametrize("cleanup", [False, True])
def test_desktop_wrapper_routes_folder_and_cleanup(tmp_path, cleanup):
    fake = tmp_path / "archivebench-desktop.cmd"
    fake.write_text("@echo off\necho ROUTED %*\nexit /b 0\n")
    source = tmp_path / "Project with spaces"
    source.mkdir()
    extra = tmp_path / "another clip.mov"
    extra.touch()
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-File",
            str(WINDOWS / "archivebench-desktop.ps1"),
            "-Root",
            str(source),
            "-PresetDirectory",
            str(tmp_path),
            *([] if cleanup else [str(extra)]),
            *(["-Cleanup"] if cleanup else []),
        ],
        env={**os.environ, "PATH": str(tmp_path) + os.pathsep + os.environ["PATH"]},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "ROUTED --root" in result.stdout
    assert str(source) in result.stdout
    assert "--preset-directory" in result.stdout
    assert ("--cleanup" in result.stdout) == cleanup
    if not cleanup:
        assert str(extra) in result.stdout


@pytest.mark.parametrize("terminal", ["conhost", "wezterm"])
def test_tui_shortcuts_do_not_launch_powershell(tmp_path, terminal):
    import sys

    if terminal == "wezterm" and not shutil.which("wezterm-gui.exe"):
        pytest.skip("WezTerm not installed")

    exe = Path(sys.executable).parent / "archivebench-tui.exe"
    assert exe.is_file()
    sendto = tmp_path / "Send to"
    result = powershell(
        WINDOWS / "install-send-to.ps1",
        "-InstallDirectory",
        tmp_path / "install",
        "-SendToDirectory",
        sendto,
        "-PresetDirectory",
        tmp_path / "presets",
        "-TuiExecutable",
        exe,
        *(["-Terminal", terminal] if terminal == "wezterm" else []),
    )
    assert result.returncode == 0, result.stderr
    for name in ("Archive footage", "Archive footage (terminal)"):
        inspection = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:TEST_LINK); $s.TargetPath; $s.Arguments",
            ],
            env={**os.environ, "TEST_LINK": str(sendto / f"{name}.lnk")},
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert inspection.returncode == 0
        assert ("conhost.exe" if terminal == "conhost" else "wezterm-gui.exe") in inspection.stdout
        assert str(exe) in inspection.stdout
        assert (
            "--fit-window" if terminal == "conhost" else "--always-new-process"
        ) in inspection.stdout
        assert "powershell" not in inspection.stdout.lower()
        assert "--config-file" not in inspection.stdout
        assert "archivebench-wezterm.lua" not in inspection.stdout
