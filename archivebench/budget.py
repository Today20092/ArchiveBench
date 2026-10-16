"""An invocation deadline shared by hashing and subprocess work."""

import subprocess
import time
import os
import signal
from contextvars import ContextVar

deadline: ContextVar[float | None] = ContextVar("benchmark_deadline", default=None)


def timeout(requested: float = 120) -> float:
    end = deadline.get()
    if end is None:
        return max(0.1, requested)
    remaining = end - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired("benchmark wall-clock budget", 0)
    return min(requested, remaining)


def capture(args: list[str], requested: float, cwd=None) -> subprocess.CompletedProcess[str]:
    """Stop the whole command tree, including Windows executable shims, at expiry."""
    allowance = timeout(requested)
    if deadline.get() is None:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=cwd,
            timeout=allowance,
        )
    with subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd,
        start_new_session=os.name != "nt",
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=allowance)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=10,
                )
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.kill()
            process.communicate()
            raise
        return subprocess.CompletedProcess(args, process.returncode, stdout, stderr)
