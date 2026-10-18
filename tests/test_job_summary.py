import json
from typing import Any

import pytest

from archivebench.job_summary import refresh_summary, write_summary
from archivebench.archive import archive


def test_summary_distinguishes_unfinished_and_reclaimable_bytes(tmp_path):
    manifest = {
        "source_root": "camera",
        "settings": {"quality": 20},
        "selected_sources": ["camera/a.mov", "camera/b.mov", "camera/c.mov"],
        "records": [
            {
                "source": "camera/a.mov",
                "status": "verified",
                "source_bytes": 1000,
                "output_bytes": 400,
            },
            {
                "source": "camera/b.mov",
                "status": "not_worth_encoding",
                "source_bytes": 1000,
                "output_bytes": 950,
            },
        ],
    }
    (tmp_path / "archive-manifest.json").write_text(json.dumps(manifest))
    report = write_summary(tmp_path).read_text(encoding="utf-8")
    assert "Unfinished: 1" in report
    assert "Replacement size reduction: 600 bytes" in report
    assert "Potential original deletion: 1000 bytes" in report
    assert "Net storage reclaimed after cleanup: 0 bytes" in report
    assert "camera/c.mov" in report


def test_interrupted_archive_saves_selection_and_summary(tmp_path):
    source = tmp_path / "camera"
    source.mkdir()
    (source / "clip.mov").write_bytes(b"not encoded")
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "version": 1,
                "type": "archive-settings",
                "encoder": "libx265",
                "quality": 20,
                "pixel_format": "yuv420p",
            }
        )
    )
    output = tmp_path / "output"
    with pytest.raises(KeyboardInterrupt):
        archive(source, output, settings, True, stop_requested=lambda: True)
    report = (output / "archive-summary.html").read_text(encoding="utf-8")
    assert "Unfinished: 1" in report
    assert "clip.mov" in report
    assert not (output / ".lock").exists()


def test_summary_refreshes_resumed_and_deleted_outcomes_and_escapes_data(tmp_path):
    records: list[dict[str, Any]] = [
        {"source": "a.mov", "status": "failed", "error": '<script src="https://bad">'},
        {"source": "b.mov", "status": "keep_original"},
        {"source": "c.mov", "status": "verified"},
    ]
    manifest: dict[str, Any] = {
        "selected_sources": ["a.mov", "b.mov", "c.mov", "d.mov"],
        "job_path": str(tmp_path / "saved.job.json"),
        "records": records,
    }
    path = tmp_path / "archive-manifest.json"
    path.write_text(json.dumps(manifest))
    report = write_summary(tmp_path).read_text(encoding="utf-8")
    assert "&lt;script" in report and "<script" not in report
    assert "1 completed files have unknown sizes" in report
    assert "Verified: 1" in report
    assert "Kept original: 1" in report
    assert "saved.job.json" in report
    manifest["records"][0] = {
        "source": "a.mov",
        "status": "original_deleted",
        "source_bytes": 1000,
        "output_bytes": 400,
    }
    manifest["records"].append({"source": "d.mov", "status": "not_worth_encoding"})
    path.write_text(json.dumps(manifest))
    report = write_summary(tmp_path).read_text(encoding="utf-8")
    assert "Unfinished: 0" in report and "Failed: 0" in report
    assert "Net storage reclaimed after cleanup: 600 bytes" in report
    assert "Potential original deletion: 0 bytes" in report


def test_legacy_partial_manifest_does_not_claim_full_selection(tmp_path):
    (tmp_path / "archive-manifest.json").write_text('{"records": []}')
    report = write_summary(tmp_path).read_text(encoding="utf-8")
    assert "Selection coverage unknown" in report
    assert "Next: inspect the checkpoint and recover the selected file list" in report


@pytest.mark.parametrize(
    ("status", "next_action"),
    [
        ("verified", "Next: inspect replacement acceptance"),
        ("failed", "Next: resolve failed files"),
        ("not_worth_encoding", "Next: keep the originals"),
        ("original_deleted", "Next: review the recorded outputs and cleanup history"),
    ],
)
def test_reopened_summary_suggests_action_from_recorded_outcome(tmp_path, status, next_action):
    manifest = {
        "source_root": "<camera>",
        "job_path": str(tmp_path / "saved.job.json"),
        "selected_sources": ["clip.mov"],
        "records": [{"source": "clip.mov", "status": status}],
    }
    (tmp_path / "archive-manifest.json").write_text(json.dumps(manifest))
    report = write_summary(tmp_path).read_text(encoding="utf-8")
    assert next_action in report
    assert "Saved evidence is not a fresh check" in report
    assert "summary authorizes neither" in report
    assert "&lt;camera&gt;" in report and "<camera>" not in report
    if status != "failed":
        assert "start/resume it" not in report


def test_summary_failure_preserves_checkpoint_and_does_not_raise(tmp_path, capsys):
    path = tmp_path / "archive-manifest.json"
    path.write_text('{"records": [{}]}')
    refresh_summary(tmp_path)
    assert path.read_text() == '{"records": [{}]}'
    assert "could not be refreshed" in capsys.readouterr().out
