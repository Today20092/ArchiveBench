"""Visible FFmpeg progress for interactive archival jobs."""

import os
import subprocess
import tempfile
import time
from collections.abc import Callable


def encode_progress(
    args: list[str], duration: float, stop_requested: Callable[[], bool] | None = None
) -> None:
    started = time.monotonic()
    with tempfile.TemporaryFile(mode="w+b") as errors:
        process = subprocess.Popen(
            [args[0], "-progress", "pipe:1", "-nostats", *args[1:]],
            stdout=subprocess.PIPE,
            stderr=errors,
            text=True,
        )
        state: dict[str, str] = {}
        try:
            assert process.stdout is not None
            for line in process.stdout:
                if stop_requested and stop_requested():
                    raise KeyboardInterrupt
                key, _, value = line.strip().partition("=")
                state[key] = value
                if key == "progress":
                    elapsed = time.monotonic() - started
                    done = max(0, float(state.get("out_time_us", "0")) / 1e6)
                    ratio = min(1, done / duration) if duration > 0 else 0
                    eta = elapsed * (1 - ratio) / ratio if ratio > 0 else None
                    print(
                        f"{ratio:.0%} | speed {state.get('speed', '?')} | elapsed {elapsed:.0f}s | remaining {eta:.0f}s"
                        if eta is not None
                        else "Starting encode...",
                        flush=True,
                    )
            if process.wait() != 0:
                errors.seek(0)
                raise RuntimeError(errors.read().decode("utf-8", errors="replace")[-8000:])
        except BaseException:
            if process.poll() is None:
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        capture_output=True,
                        timeout=10,
                    )
                process.kill()
                process.wait()
            raise
