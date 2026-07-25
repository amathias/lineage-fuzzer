from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

DENIED_TRACKED_NAMES = {".env", "id_rsa", "id_ed25519"}
IGNORED_PARTS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".verify-dist",
    ".verify-venv",
    "__pycache__",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\."),
}


def tracked_files(root: Path) -> tuple[Path, ...]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return tuple(
            path
            for path in root.rglob("*")
            if path.is_file()
            and not any(part in IGNORED_PARTS for part in path.relative_to(root).parts)
        )
    return tuple(root / item.decode("utf-8") for item in result.stdout.split(b"\0") if item)


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in tracked_files(root):
        if path.name in DENIED_TRACKED_NAMES:
            findings.append(f"denied tracked secret filename: {path.relative_to(root)}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {path.relative_to(root)}")
    return findings


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = scan(root)
    if findings:
        print("\n".join(findings), file=sys.stderr)
        return 1
    print(f"secret_scan=clean tracked_files={len(tracked_files(root))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
