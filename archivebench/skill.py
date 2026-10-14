"""Install the portable skill bundled with the same ArchiveBench release."""

import argparse
import shutil
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination", type=Path, required=True, help="Your client's skill directory"
    )
    args = parser.parse_args()
    bundled = Path(__file__).parent / "_skill"
    source = bundled if bundled.is_dir() else Path(__file__).parents[1] / "skills/archivebench"
    target = args.destination.expanduser().resolve() / "archivebench"
    try:
        if target.exists():
            raise ValueError(f"Skill already exists: {target}; review it before replacing it")
        if not (source / "SKILL.md").is_file():
            raise ValueError("This installation has no bundled skill; reinstall the release wheel")
        shutil.copytree(source, target)
    except (OSError, ValueError) as error:
        print(f"ArchiveBench: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(f"Installed skill: {target}")
    print("Enable it in your client, then locate archivebench and run archivebench doctor.")


if __name__ == "__main__":
    main()
