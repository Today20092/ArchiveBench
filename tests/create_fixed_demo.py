"""Synthetic fixed-comparison report for browser checks; no camera media."""

from pathlib import Path

from archivebench.core import benchmark, run, save

root = Path("runs/fixed-demo").resolve()
root.mkdir(parents=True, exist_ok=True)
source = root / "synthetic.mkv"
if not source.exists():
    run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=640x360:rate=30",
            "-t",
            "8",
            "-c:v",
            "ffv1",
            "-pix_fmt",
            "yuv422p10le",
            str(source),
        ]
    )
config = {
    "version": 1,
    "strategy": "fixed",
    "review_mode": "full",
    "mode": "quick",
    "profile": "editing",
    "budget_minutes": 3,
    "pixel_format": "yuv420p10le",
    "resolution": "original",
    "samples": [{"path": str(source), "label": "Synthetic motion", "start": 0, "seconds": 5}],
    "encoders": ["libx265", "libsvtav1", "hevc_nvenc"],
    "encode_repeats": 1,
}
save(root / "config.json", config)
result = benchmark(root / "config.json", root / "benchmark")
print(
    {
        "status": result["status"],
        "trials": len(result["trials"]),
        "report": str(root / "benchmark/report.html"),
    }
)
