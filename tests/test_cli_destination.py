import json
import sys

import pytest

from archivebench.cli import main
from archivebench.core import save
from archivebench.jobs import create_job


def test_cli_creation_resumes_destination_and_reports_conflicting_settings(
    tmp_path, monkeypatch, capsys
):
    source = tmp_path / "source"
    source.mkdir()
    (source / "clip.mov").touch()
    preset = tmp_path / "preset.json"
    settings = {
        "version": 2,
        "type": "archive-settings",
        "encoder": "libx264",
        "quality": 24,
        "pixel_format": "source",
    }
    save(preset, settings)
    output = tmp_path / "output"
    saved = create_job(source, output, preset)
    saved.update(selected_files=["clip.mov"], continue_on_error=True, progress=True)
    save(output / "archive-job.json", saved)
    config = tmp_path / "resumed.json"
    args = [
        "archivebench",
        "job",
        "create",
        str(config),
        "--source",
        str(source),
        "--output",
        str(output),
        "--preset",
        str(preset),
    ]
    monkeypatch.setattr(sys, "argv", args)
    main()
    assert json.loads(config.read_text()) == saved
    assert "Resuming" in capsys.readouterr().out
    save(preset, {**settings, "quality": 30})
    config.unlink()
    with pytest.raises(SystemExit):
        main()
    assert "settings conflict" in capsys.readouterr().err
    assert not config.exists()
