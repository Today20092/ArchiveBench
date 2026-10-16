from archivebench.desktop import selection_defaults, selected_job
from archivebench.core import save
from archivebench.presets import make_preset


def test_mixed_selection_preserves_paths_and_deduplicates(tmp_path):
    files = []
    for card in ("SD 1", "SD 2", "SSD"):
        path = tmp_path / card / "nested" / "same.mov"
        path.parent.mkdir(parents=True)
        path.touch()
        files.append(path)
    root, output, rows = selection_defaults(
        [tmp_path / "SD 1", tmp_path / "SD 2", files[0], files[2]]
    )
    assert root == tmp_path
    assert output == tmp_path / "Archived Footage"
    assert [p for p, checked in rows if checked] == files
    assert selection_defaults([files[0]])[0] == files[0].parent
    assert selection_defaults([tmp_path / "SD 1", files[0]])[0] == tmp_path / "SD 1"

    preset = tmp_path / "preset.json"
    save(
        preset,
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 24,
                "pixel_format": "source",
            }
        ),
    )
    selected = [p.relative_to(root).as_posix() for p in files]
    first = selected_job(root, output, preset, selected, {})
    repeated = selected_job(root, output, preset, list(reversed(selected)) + [selected[0]], {})
    assert first == repeated
    assert first["selected_files"] == selected


def test_invalid_selection_is_rejected(tmp_path):
    import pytest

    with pytest.raises(ValueError):
        selection_defaults([])
    invalid = tmp_path / "notes.txt"
    invalid.touch()
    with pytest.raises(ValueError, match="Unsupported"):
        selection_defaults([invalid])


def test_window_adds_sources_without_resetting_checkmarks(tmp_path, monkeypatch):
    from archivebench.desktop import window, filedialog
    from tkinter import ttk

    first, second = tmp_path / "SD 1", tmp_path / "SD 2"
    first.mkdir()
    second.mkdir()
    (first / "same.mov").touch()
    (second / "same.mov").touch()
    library = tmp_path / "presets"
    save(
        library / "preset.json",
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 24,
                "pixel_format": "source",
            }
        ),
    )
    form, result = window(first, library)
    form.withdraw()
    try:

        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)

        widgets = list(descendants(form))
        tree = next(w for w in widgets if isinstance(w, ttk.Treeview))
        buttons = {w.cget("text"): w for w in widgets if isinstance(w, ttk.Button)}
        buttons["Select none"].invoke()
        monkeypatch.setattr(filedialog, "askdirectory", lambda: str(second))
        buttons["Add folder"].invoke()
        rows = [tree.item(k)["values"] for k in tree.get_children()]
        assert [(r[0], r[1]) for r in rows] == [("No", "SD 1/same.mov"), ("Yes", "SD 2/same.mov")]
        monkeypatch.setattr(filedialog, "askopenfilenames", lambda: [str(second / "same.mov")])
        buttons["Add files"].invoke()
        assert len(tree.get_children()) == 2
        assert result == {}
    finally:
        form.destroy()


def test_multi_folder_encode_and_resume(tmp_path):
    import json
    import shutil
    import subprocess
    import pytest
    from archivebench.jobs import run_job

    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg required")
    folders = [tmp_path / "SD 1", tmp_path / "SD 2"]
    for folder in folders:
        folder.mkdir()
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
            str(folders[0] / "same.mkv"),
        ],
        check=True,
    )
    shutil.copyfile(folders[0] / "same.mkv", folders[1] / "same.mkv")
    root, output, rows = selection_defaults([*folders, folders[0] / "same.mkv"])
    preset = tmp_path / "preset.json"
    save(
        preset,
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 30,
                "pixel_format": "source",
            }
        ),
    )
    job_path = tmp_path / "job.json"
    save(
        job_path,
        selected_job(root, output, preset, [p.relative_to(root).as_posix() for p, _ in rows], {}),
    )
    run_job(job_path, True, accept_uncertain_suitability=True)
    records = json.loads((output / "archive-manifest.json").read_text())["records"]
    assert len(records) == 2 and all(r["status"] == "verified" for r in records)
    from pathlib import Path

    timestamps = {r["output"]: Path(r["output"]).stat().st_mtime_ns for r in records}
    assert {Path(p).parent.name for p in timestamps} == {"SD 1", "SD 2"}
    run_job(job_path, True)
    assert timestamps == {p: Path(p).stat().st_mtime_ns for p in timestamps}
    assert all((folder / "same.mkv").exists() for folder in folders)


def test_destination_discovers_saved_job_and_rejects_conflicts(tmp_path):
    import pytest
    from archivebench.jobs import discover_job

    source = tmp_path / "source"
    source.mkdir()
    (source / "clip.mov").write_bytes(b"original")
    preset = tmp_path / "preset.json"
    save(
        preset,
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 24,
                "pixel_format": "source",
            }
        ),
    )
    output = tmp_path / "output"
    job = selected_job(source, output, preset, ["clip.mov"], {})
    assert discover_job(output) is None
    save(
        output / "archive-manifest.json",
        {"job": job, "source_root": str(source), "output_root": str(output)},
    )
    assert discover_job(output) == job
    assert selected_job(source, output, preset, ["clip.mov"], {}) == job
    with pytest.raises(ValueError, match="settings.*another destination"):
        selected_job(source, output, preset, ["clip.mov"], {"quality": 30})
    (source / "second.mov").write_bytes(b"original")
    with pytest.raises(ValueError, match="selection.*another destination"):
        selected_job(source, output, preset, ["clip.mov", "second.mov"], {})


def test_selected_archive_roots_are_excluded(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    original = source / "clip.mov"
    original.touch()
    generated = source / "delivery"
    generated.mkdir()
    (generated / "old.mov").touch()
    save(generated / "archive-manifest.json", {})
    root, _, rows = selection_defaults([source, generated])
    assert root == source
    assert rows == [(original, True)]
    assert selection_defaults([generated])[2] == []
    nested = generated / "nested"
    nested.mkdir()
    (nested / "old.mov").touch()
    assert selection_defaults([nested])[2] == []


def test_destination_discovers_preexecution_job_and_legacy_selection(tmp_path):
    from archivebench.jobs import create_job, discover_job

    source = tmp_path / "source"
    source.mkdir()
    (source / "clip.mov").touch()
    preset = tmp_path / "preset.json"
    save(
        preset,
        make_preset(
            {
                "version": 2,
                "type": "archive-settings",
                "encoder": "libx264",
                "quality": 24,
                "pixel_format": "source",
            }
        ),
    )
    output = tmp_path / "output"
    saved = create_job(source, output, preset)
    save(tmp_path / "output.job.json", saved)
    assert discover_job(output) == saved
    assert selected_job(source, output, preset, ["clip.mov"], {}) == saved
