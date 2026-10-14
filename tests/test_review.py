import json
import shutil
import sys

import pytest

from archivebench.core import digest, run, save
from archivebench.cli import main
from archivebench.report import write_report
from archivebench.review import (
    inspect_review,
    record_review,
    saved_reviews,
    decoded_alignment,
    launch_review,
)


@pytest.fixture
def review_run(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("FFmpeg required")
    folder = tmp_path / "sample-1"
    folder.mkdir()
    reference = folder / "reference.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=96x64:rate=24",
            "-t",
            "1",
            "-c:v",
            "ffv1",
            str(reference),
        ]
    )
    candidate = folder / "candidate with spaces.mkv"
    shutil.copyfile(reference, candidate)
    save(folder / "reference.json", {"sha256": digest(reference)})
    save(
        tmp_path / "results.json",
        {
            "identity": "synthetic-run",
            "config": {"samples": [{"path": "source.mov", "start": 3}]},
            "samples": [{"id": "sample-1", "start": 3, "seconds": 1, "source_id": "source-1"}],
            "trials": [
                {
                    "id": "trial-1",
                    "sample": "sample-1",
                    "output": str(candidate),
                    "sha256": digest(candidate),
                }
            ],
        },
    )
    return tmp_path


def test_review_decision_survives_reopen_and_changed_media_invalidates_it(review_run):
    record_review(review_run, "trial-1", "reject", "Editor", [0.25], "Banding", "native")
    assert saved_reviews(review_run)[0]["decision"] == "reject"
    assert saved_reviews(review_run)[0]["objections"] == [0.25]
    path = review_run / "sample-1" / "candidate with spaces.mkv"
    path.write_bytes(path.read_bytes() + b"changed")
    assert saved_reviews(review_run)[0]["status"] == "invalid"


def test_review_rejects_out_of_interval_moments_and_external_paths(review_run):
    with pytest.raises(ValueError, match="interval"):
        record_review(review_run, "trial-1", "accept", "Editor", [1.5], "", "native")
    result = json.loads((review_run / "results.json").read_text())
    result["trials"][0]["output"] = str(review_run.parent / "outside.mkv")
    save(review_run / "results.json", result)
    with pytest.raises(ValueError, match="outside"):
        inspect_review(review_run, "trial-1")


def test_exact_pair_alignment_and_missing_viewer_fallback(review_run):
    pair = inspect_review(review_run, "trial-1")
    checked = decoded_alignment(pair)
    assert checked["frames"] == 24
    assert checked["reference"]["width"] == 96
    assert checked["display_fidelity"] == "unverified"
    with pytest.raises(ValueError, match="browser"):
        launch_review(review_run, "trial-1", "archivebench-nonexistent-viewer")


def test_launch_uses_argv_and_cannot_imply_acceptance(review_run, monkeypatch):
    class Viewer:
        pid = 123

        def __init__(self, command, **options):
            assert isinstance(command, list)
            assert command[-1].endswith("candidate with spaces.mkv")
            assert "--no-auto-filters" in command
            assert options["shell"] is False

        def wait(self, timeout):
            raise __import__("subprocess").TimeoutExpired("viewer", timeout)

    import subprocess

    original = subprocess.Popen
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda command, **options: (
            Viewer(command, **options)
            if command[0] == "viewer.exe"
            else original(command, **options)
        ),
    )
    # Inspection and decoding are real; replace only the external viewer launch boundary.
    monkeypatch.setattr("shutil.which", lambda value: "viewer.exe")
    assert launch_review(review_run, "trial-1")["visual_acceptance"] == "unreviewed"


def test_terminal_review_and_report_preserve_decisions_safely(review_run, monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "archivebench",
            "review",
            "inspect",
            "--results",
            str(review_run / "results.json"),
            "--trial",
            "trial-1",
        ],
    )
    main()
    assert json.loads(capsys.readouterr().out)["interval"] == {"start": 3, "seconds": 1}
    record_review(
        review_run, "trial-1", "accept", "Editor", [], "<script>unsafe</script>", "browser"
    )
    result = json.loads((review_run / "results.json").read_text())
    result.update(status="complete", skipped=[])
    result["config"].update(pixel_format="source", resolution="original", target_vmaf=95)
    result["trials"][0].update(
        encoder="libx264", quality=24, vmaf=95, ssim=0.99, bytes=1234, encode_seconds=1
    )
    html = write_report(result, review_run).read_text(encoding="utf-8")
    assert "Saved visual decisions" in html
    assert "accept (current, browser)" in html
    assert "&lt;script&gt;unsafe&lt;/script&gt;" in html
    assert "<script>unsafe</script>" not in html


def test_native_alignment_rejects_different_frame_count(review_run):
    candidate = review_run / "sample-1" / "candidate with spaces.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=red:size=96x64:rate=24",
            "-t",
            "0.5",
            "-c:v",
            "ffv1",
            str(candidate),
        ]
    )
    result = json.loads((review_run / "results.json").read_text())
    result["trials"][0]["sha256"] = digest(candidate)
    save(review_run / "results.json", result)
    with pytest.raises(ValueError, match="align"):
        decoded_alignment(inspect_review(review_run, "trial-1"))
