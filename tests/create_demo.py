"""Generate synthetic demonstration footage and a real report, never personal media."""

from pathlib import Path

from archivebench.core import benchmark, run, save
from archivebench.report import write_report


def main() -> None:
    root = Path("runs/demo").resolve()
    root.mkdir(parents=True, exist_ok=True)
    source = root / "synthetic-motion.mov"
    if not source.exists():
        run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=640x360:rate=30",
                "-t",
                "4",
                "-c:v",
                "libx264",
                "-crf",
                "0",
                "-pix_fmt",
                "yuv422p10le",
                "-color_range",
                "pc",
                "-colorspace",
                "bt709",
                "-color_trc",
                "bt709",
                "-color_primaries",
                "bt709",
                str(source),
            ]
        )
    config = {
        "version": 1,
        "mode": "quick",
        "profile": "compact",
        "pixel_format": "yuv420p10le",
        "target_vmaf": 93,
        "budget_minutes": 4,
        "samples": [
            {
                "path": str(source),
                "label": "Synthetic motion · demo, not camera footage",
                "start": 0,
                "seconds": 2,
            }
        ],
        "encoders": ["libx265", "libsvtav1", "hevc_nvenc"],
    }
    save(root / "config.json", config)
    result = benchmark(root / "config.json", root / "benchmark")
    print(write_report(result, root / "benchmark"))


if __name__ == "__main__":
    main()
