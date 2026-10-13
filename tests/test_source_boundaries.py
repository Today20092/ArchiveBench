from archivebench.core import benchmark, save

import pytest


def test_run_folder_cannot_contain_selected_original(tmp_path):
    output = tmp_path / "run"
    source = output / "match-source" / "sample-1" / "libx264-q23" / "encoded.mkv"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"original footage must stay intact")
    config_path = tmp_path / "config.json"
    save(
        config_path,
        {
            "version": 1,
            "profile": "compact",
            "mode": "quick",
            "pixel_format": "yuv420p",
            "target_vmaf": 93,
            "budget_minutes": 1,
            "ffmpeg": "missing-test-executable",
            "samples": [{"path": str(source), "start": 0, "seconds": 1}],
        },
    )
    with pytest.raises(ValueError, match="contains a selected source"):
        benchmark(config_path, output)
    assert source.read_bytes() == b"original footage must stay intact"
    assert not (output / "results.json").exists()
    assert not (output / ".lock").exists()
