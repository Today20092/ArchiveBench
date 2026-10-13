import pytest
import shutil
from archivebench.core import benchmark, digest, run, save

from archivebench.core import validate_config


def test_saved_experiment_accepts_named_variants_and_rejects_ambiguous_ids(tmp_path):
    source = tmp_path / "clip.mkv"
    source.touch()
    config = {
        "version": 1,
        "profile": "compact",
        "mode": "quick",
        "budget_minutes": 1,
        "samples": [{"path": str(source), "start": 0, "seconds": 1}],
        "variants": [
            {
                "id": "match-source",
                "label": "Match source",
                "pixel_format": "source",
                "resolution": "original",
            },
            {"id": "small", "label": "Small", "pixel_format": "yuv420p", "resolution": "720p"},
        ],
    }
    validate_config(config)
    config["variants"][1]["id"] = "match-source"
    with pytest.raises(ValueError, match="unique"):
        validate_config(config)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="FFmpeg integration test")
def test_shared_candidates_cover_different_sources_and_keep_source_identity(tmp_path):
    sources = [tmp_path / "motion.mkv", tmp_path / "flat.mkv"]
    for source, pattern, duration in zip(
        sources,
        ["testsrc2=size=160x90:rate=24", "color=black:size=160x90:rate=24"],
        [2, 3],
        strict=True,
    ):
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                pattern,
                "-t",
                str(duration),
                "-c:v",
                "ffv1",
                str(source),
            ]
        )
    hashes = [digest(source) for source in sources]
    config = {
        "version": 1,
        "profile": "compact",
        "mode": "quick",
        "pixel_format": "yuv420p",
        "target_vmaf": 98,
        "budget_minutes": 3,
        "encoders": ["libx264"],
        "samples": [
            {"path": str(sources[0]), "start": 0, "seconds": 0.5},
            {"path": str(sources[0]), "start": 1, "seconds": 0.5},
            {"path": str(sources[1]), "start": 0, "seconds": 0.5},
        ],
    }
    config_path = tmp_path / "experiment.json"
    save(config_path, config)
    result = benchmark(config_path, tmp_path / "benchmark")
    assert result["status"] == "completed", result["skipped"]
    candidates = {(row["encoder"], row["quality"], row["variant"]) for row in result["trials"]}
    assert len(candidates) > 1
    for encoder, quality, variant in candidates:
        assert {
            row["sample"]
            for row in result["trials"]
            if (row["encoder"], row["quality"], row["variant"]) == (encoder, quality, variant)
        } == {"sample-1", "sample-2", "sample-3"}
    assert result["samples"][0]["source_id"] == result["samples"][1]["source_id"]
    assert result["samples"][0]["source_id"] != result["samples"][2]["source_id"]
    assert result["samples"][0]["source_seconds"] == 2
    assert result["samples"][2]["source_seconds"] == 3
    assert [digest(source) for source in sources] == hashes
    assert len(benchmark(config_path, tmp_path / "benchmark")["trials"]) == len(result["trials"])
