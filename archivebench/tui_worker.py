"""Run the shared engine in isolation; stdin stop/EOF requests safe cancellation."""

import argparse
import _thread
import sys
import threading
from pathlib import Path

from .jobs import run_job


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("job", type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--comparison", action="store_true")
    args = parser.parse_args()
    stopped = threading.Event()

    def control():
        # A closed TUI pipe is also a stop request; never keep encoding orphaned.
        sys.stdin.readline()
        stopped.set()
        if args.comparison:
            _thread.interrupt_main()

    threading.Thread(target=control, daemon=True).start()
    try:
        if args.comparison:
            from .core import benchmark

            result = benchmark(args.job, args.job.parent)
            print(
                f"Comparison status: {result.get('status')}; inspect report evidence before selecting settings",
                flush=True,
            )
        else:
            run_job(args.job, args.execute, stop_requested=stopped.is_set)
    except KeyboardInterrupt:
        print(
            "Stopped safely. Completed records remain; interrupted clips restart on resume.",
            flush=True,
        )
        return 130
    except Exception as error:
        print(f"Failed: {error}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
