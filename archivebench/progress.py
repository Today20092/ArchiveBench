"""Visible FFmpeg progress for interactive archival jobs."""

import os
import subprocess
import tempfile
import time
from queue import Empty, Queue
from threading import Thread
from collections.abc import Callable


def encode_progress(
    args: list[str],
    duration: float,
    stop_requested: Callable[[], bool] | None = None,
    *,
    check_storage: Callable[[], None] | None = None,
    visible: bool = True,
    timeout: float = 86400,
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
        lines: Queue[str | None] = Queue()

        def read_progress() -> None:
            assert process.stdout is not None
            try:
                for line in process.stdout:
                    lines.put(line)
            finally:
                lines.put(None)

        reader = Thread(target=read_progress, daemon=True)
        reader.start()
        try:
            while True:
                if time.monotonic() - started >= timeout:
                    raise TimeoutError("Encode time limit exceeded; stopping batch")
                if stop_requested and stop_requested():
                    raise KeyboardInterrupt
                if check_storage:
                    check_storage()
                try:
                    line = lines.get(timeout=0.25)
                except Empty:
                    continue
                if line is None:
                    break
                key, _, value = line.strip().partition("=")
                state[key] = value
                if key == "progress" and visible:
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
                    try:
                        subprocess.run(
                            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            capture_output=True,
                            timeout=10,
                        )
                    except (OSError, subprocess.TimeoutExpired):
                        pass
                if process.poll() is None:
                    process.kill()
                process.wait()
            raise
        finally:
            reader.join(timeout=2)
            if process.stdout is not None:
                process.stdout.close()
