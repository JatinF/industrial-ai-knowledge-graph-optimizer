"""Locate the repository root from a source checkout or the container image."""

import os
from pathlib import Path


def repo_root() -> Path:
    override = os.environ.get("INDUSTRIAL_AI_ROOT")
    if override:
        return Path(override)
    marker = Path("datasets") / "scenarios" / "machine_failure.json"
    for parent in Path(__file__).resolve().parents:
        if (parent / marker).is_file():
            return parent
    cwd = Path.cwd()
    if (cwd / marker).is_file():
        return cwd
    raise FileNotFoundError("repository root not found")
