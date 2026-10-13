import pytest

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
