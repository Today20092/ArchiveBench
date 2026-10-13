import shutil
from typing import Any

import pytest

from archivebench.core import digest, run, save
from archivebench.stills import generate_stills


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg integration")
def test_review_pairs_measured_frames_at_native_sizes(tmp_path):
    reference_dir = tmp_path / "sample-1"
    reference_dir.mkdir()
    reference = reference_dir / "reference.mkv"
    encoded = tmp_path / "encoded.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=160x90:rate=30000/1001",
            "-frames:v",
            "90",
            "-c:v",
            "ffv1",
            str(reference),
        ]
    )
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(reference),
            "-vf",
            "scale=80:46",
            "-c:v",
            "ffv1",
            str(encoded),
        ]
    )
    save(reference_dir / "reference.json", {"sha256": digest(reference)})
    trial: dict[str, Any] = {
        "id": "a",
        "sample": "sample-1",
        "variant": "source",
        "encoder": "libx264",
        "quality": 24,
        "output": str(encoded),
        "sha256": digest(encoded),
        "width": 80,
        "height": 46,
        "vmaf_frames": [{"frame_index": n, "vmaf": 50 + n / 100} for n in (5, 10, 40, 80)],
    }
    result = {
        "validation_shortlist": [
            {
                "variant": "source",
                "encoder": "libx264",
                "quality": 24,
                "evidence_status": "validated",
            }
        ],
        "trials": [trial],
        "samples": [{"id": "sample-1", "video": {"fps": "30000/1001", "width": 160, "height": 90}}],
    }
    generate_stills(result, tmp_path, lambda: 60)
    evidence = trial["review_stills"]
    assert evidence["status"] == "complete"
    assert [m["frame_index"] for m in evidence["moments"]] == [5, 40, 80]
    assert evidence["moments"][0]["seconds"] == pytest.approx(5 * 1001 / 30000)
    for moment in evidence["moments"]:
        for kind, source in (("original", reference), ("encoded", encoded)):
            expected = tmp_path / f"expected-{kind}.png"
            run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(source),
                    "-vf",
                    f"select=eq(n\\,{moment['frame_index']})",
                    "-frames:v",
                    "1",
                    "-fps_mode",
                    "passthrough",
                    str(expected),
                ]
            )
            assert digest(tmp_path / moment[kind]["path"]) == digest(expected)
    generate_stills(result, tmp_path, lambda: 60)
    assert trial["review_stills"]["status"] == "complete"
    (tmp_path / evidence["moments"][0]["original"]["path"]).write_bytes(b"changed")
    generate_stills(result, tmp_path, lambda: 0)
    assert trial["review_stills"]["status"] == "incomplete"
    trial["vmaf_frames"] = [{"frame_index": 40, "vmaf": 75}]
    generate_stills(result, tmp_path, lambda: 60)
    assert len(trial["review_stills"]["moments"]) == 1
    assert "Only 1 separated" in trial["review_stills"]["note"]
    result["validation_shortlist"][0]["evidence_status"] = "failed"
    trial.pop("review_stills")
    generate_stills(result, tmp_path, lambda: 60)
    assert "review_stills" not in trial


def test_exhausted_budget_skips_input_hashing(tmp_path, monkeypatch):
    def unexpected_hash(path):
        pytest.fail("Exhausted review must not hash inputs")

    monkeypatch.setattr("archivebench.core.digest", unexpected_hash)
    trial: dict[str, Any] = {
        "id": "a",
        "sample": "sample-1",
        "variant": "source",
        "encoder": "libx264",
        "quality": 24,
        "output": str(tmp_path / "missing.mkv"),
        "sha256": "missing",
        "vmaf_frames": [],
    }
    result = {
        "validation_shortlist": [
            {
                "variant": "source",
                "encoder": "libx264",
                "quality": 24,
                "evidence_status": "validated",
            }
        ],
        "trials": [trial],
        "samples": [{"id": "sample-1", "video": {"fps": "30", "width": 160, "height": 90}}],
    }
    generate_stills(result, tmp_path, lambda: 0.1)
    assert trial["review_stills"]["status"] == "incomplete"
    assert result["validation_shortlist"][0]["evidence_status"] == "validated"
