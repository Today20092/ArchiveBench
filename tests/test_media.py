from archivebench.media import safe_asset_path
from pathlib import Path
from typing import Any
import shutil

import pytest

from archivebench.core import digest, fingerprint, run, save
from archivebench.media import generate_review_media


def test_companion_paths_reject_external_and_escaped_locations():
    assert safe_asset_path("review/abc/original.mp4")
    for path in [
        "../clip.mp4",
        "/clip.mp4",
        "https://x/a",
        "review/a%2fb",
        "review/a?x",
        "review/../a",
        "review\\a",
        "C:/a",
    ]:
        assert not safe_asset_path(path)


def test_preview_temporary_symlink_cannot_overwrite_original(tmp_path: Path, monkeypatch):
    root = tmp_path / "run"
    reference = root / "sample-1" / "reference.mkv"
    reference.parent.mkdir(parents=True)
    reference.write_bytes(b"reference")
    save(reference.with_name("reference.json"), {"sha256": digest(reference)})
    encoded = root / "trial.mkv"
    encoded.write_bytes(b"encoded")
    trial: dict[str, Any] = {
        "id": "trial-1",
        "sample": "sample-1",
        "variant": "source",
        "encoder": "libx264",
        "quality": 18,
        "output": str(encoded),
        "sha256": digest(encoded),
    }
    folder = root / "review" / fingerprint({"trial": trial["id"], "sha256": trial["sha256"]})[:20]
    folder.mkdir(parents=True)
    original = tmp_path / "original.mov"
    original.write_bytes(b"preserve original")
    temporary = folder / "original-partial.mp4"
    try:
        temporary.symlink_to(original)
    except OSError:
        pytest.skip("Symlinks are unavailable")
    calls = []

    def unsafe_encoder(command, timeout):
        calls.append(command)
        Path(command[-1]).write_bytes(b"overwritten")
        raise RuntimeError("Simulated encoding failure")

    monkeypatch.setattr("archivebench.core.run", unsafe_encoder)
    result = {
        "config": {},
        "samples": [{"id": "sample-1", "video": {"frames": 1, "fps": "24"}}],
        "trials": [trial],
        "validation_shortlist": [
            {
                "variant": "source",
                "encoder": "libx264",
                "quality": 18,
                "evidence_status": "validated",
            }
        ],
    }
    generate_review_media(result, root, lambda: 60)
    assert original.read_bytes() == b"preserve original"
    assert calls == []
    assert trial["review_media"]["status"] == "unavailable"
    assert result["validation_shortlist"][0]["evidence_status"] == "validated"


def test_validated_finalists_get_fractional_rate_paired_previews(tmp_path: Path):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("FFmpeg is unavailable")
    reference = tmp_path / "sample-1" / "reference.mkv"
    reference.parent.mkdir()
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
            "60",
            "-c:v",
            "ffv1",
            str(reference),
        ]
    )
    save(reference.with_name("reference.json"), {"sha256": digest(reference)})
    exact = tmp_path / "trial.mkv"
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(reference),
            "-vf",
            "scale=80:44",
            "-c:v",
            "libx264",
            str(exact),
        ]
    )
    result: dict[str, Any] = {
        "config": {},
        "samples": [{"id": "sample-1", "video": {"frames": 60, "fps": "30000/1001"}}],
        "trials": [
            {
                "id": "trial-1",
                "sample": "sample-1",
                "variant": "source",
                "encoder": "libx264",
                "quality": 18,
                "output": str(exact),
                "sha256": digest(exact),
            }
        ],
        "validation_shortlist": [
            {
                "variant": "source",
                "encoder": "libx264",
                "quality": 18,
                "evidence_status": "validated",
            }
        ],
    }
    generate_review_media(result, tmp_path, lambda: 60)
    media: dict[str, Any] = result.get("trials", [])[0]["review_media"]
    assert media["status"] == "available"
    assert media["original"]["width"] == 160
    assert media["encoded"]["width"] == 80
    assert media["encoded"]["frames"] == 60
    assert digest(tmp_path / media["exact"]["path"]) == digest(exact)
    original_modified = (tmp_path / media["original"]["path"]).stat().st_mtime_ns
    trials: list[dict[str, Any]] = result.get("trials", [])
    trials.append({**trials[0], "id": "trial-2", "review_media": None})
    generate_review_media(result, tmp_path, lambda: 60)
    assert trials[1]["review_media"]["original"] == media["original"]
    assert (tmp_path / media["original"]["path"]).stat().st_mtime_ns == original_modified
    (tmp_path / media["original"]["path"]).write_bytes(b"tampered")
    generate_review_media(result, tmp_path, lambda: 60)
    assert result.get("trials", [])[0]["review_media"]["status"] == "unavailable"
    assert (tmp_path / media["original"]["path"]).read_bytes() == b"tampered"
    generate_review_media(result, tmp_path, lambda: 0)
    unavailable: dict[str, Any] = result.get("trials", [])[0]["review_media"]
    assert unavailable["status"] == "unavailable"
    assert result["validation_shortlist"][0]["evidence_status"] == "validated"
