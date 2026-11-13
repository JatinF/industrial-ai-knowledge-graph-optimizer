"""Fail when a file contains a private-key marker.

The markers are split in this source file so the scanner does not match itself.
"""

import sys
from pathlib import Path

MARKERS = (
    "-----BEGIN " + "PRIVATE KEY-----",
    "-----BEGIN " + "RSA PRIVATE KEY-----",
    "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
    "-----BEGIN " + "EC PRIVATE KEY-----",
)

SKIP_PARTS = {".git", ".venv", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
SKIP_SUFFIXES = {".png", ".pyc", ".whl", ".zip"}


def scan(root: Path) -> list[Path]:
    hits: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if not path.is_file() or path.suffix.lower() in SKIP_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(marker in text for marker in MARKERS):
            hits.append(path)
    return hits


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]) if args else Path.cwd()
    hits = scan(root)
    if hits:
        print(f"private key marker in {len(hits)} file(s)")
        return 1
    print("no private key markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
