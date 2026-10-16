"""Install the optional Windows shortcut without changing the archive engine."""

import argparse
import os
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Install Windows Send to > ArchiveBench")
    parser.add_argument("--install", action="store_true", required=True)
    parser.add_argument("--preset-directory", type=Path)
    parser.add_argument("--terminal", choices=("conhost", "wezterm"), default="conhost")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Send to is available on Windows only")
    command = [
        "powershell.exe",
        "-NoProfile",
        "-File",
        str(Path(__file__).parent / "windows" / "install-send-to.ps1"),
        "-Terminal",
        args.terminal,
    ]
    if args.preset_directory:
        command += ["-PresetDirectory", str(args.preset_directory.resolve())]
    raise SystemExit(subprocess.run(command, check=False).returncode)


if __name__ == "__main__":
    main()
