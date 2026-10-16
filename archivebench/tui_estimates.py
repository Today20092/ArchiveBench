"""Read-only duration probes and historical video encoding estimates."""

import asyncio
import json
import math
import subprocess
import sys
from pathlib import Path


def measured_rate(document: dict) -> float | None:
    evidence = document.get("evidence", {}).get("estimates", {})
    if not isinstance(evidence, dict):
        return None
    rate = evidence.get("encode_seconds_per_second")
    if (
        evidence.get("basis") == "measured"
        and isinstance(rate, (int, float))
        and not isinstance(rate, bool)
        and math.isfinite(rate)
        and rate > 0
    ):
        return float(rate)
    return None


def duration_label(seconds: float) -> str:
    seconds = math.ceil(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


async def clip_duration(path: Path) -> float | None:
    process = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=duration:format=duration",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(), 30)
        if process.returncode:
            return None
        info = json.loads(output)
        if not info.get("streams"):
            return None
        for value in (info["streams"][0].get("duration"), info.get("format", {}).get("duration")):
            try:
                seconds = float(value)
            except (TypeError, ValueError):
                continue
            if math.isfinite(seconds) and seconds > 0:
                return seconds
        return None
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
