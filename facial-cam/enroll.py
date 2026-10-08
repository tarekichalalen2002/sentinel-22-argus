"""Thin wrapper — prefer: python facial-cam/main.py enroll ..."""

from __future__ import annotations

import sys
from pathlib import Path

# Delegate to main enroll subcommand
sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import main as facial_main  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else sys.argv[1:]
    return facial_main(["enroll", *args])


if __name__ == "__main__":
    raise SystemExit(main())
