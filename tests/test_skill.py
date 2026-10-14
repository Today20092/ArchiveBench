import re
import subprocess
import sys


def test_skill_install_resolves_resources_outside_checkout(tmp_path):
    destination = tmp_path / "agent skills"
    result = subprocess.run(
        [sys.executable, "-m", "archivebench.skill", "--destination", str(destination)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    root = destination / "archivebench"
    entry = (root / "SKILL.md").read_text(encoding="utf-8")
    assert entry.startswith("---\nname: archivebench\n")
    for path in root.rglob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not target.startswith("https://"):
                assert (path.parent / target.split("#")[0]).is_file(), (path, target)
    help_result = subprocess.run(
        [sys.executable, "-m", "archivebench.cli", "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert help_result.returncode == 0
    assert "benchmark" in help_result.stdout
    again = subprocess.run(
        [sys.executable, "-m", "archivebench.skill", "--destination", str(destination)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert again.returncode == 1
    assert "already exists" in again.stderr
    assert (root / "SKILL.md").read_text(encoding="utf-8") == entry
