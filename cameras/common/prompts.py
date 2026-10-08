"""Interactive terminal prompts for camera clients."""

from __future__ import annotations

import getpass
import sys
from pathlib import Path


def ask(label: str, *, default: str | None = None, secret: bool = False) -> str:
    hint = f" [{default}]" if default else ""
    prompt = f"{label}{hint}: "
    if secret:
        value = getpass.getpass(prompt)
    else:
        value = input(prompt)
    value = (value or "").strip()
    if not value and default is not None:
        return default
    return value


def ask_required(label: str, *, secret: bool = False) -> str:
    while True:
        value = ask(label, secret=secret)
        if value:
            return value
        print("  (required)", file=sys.stderr)


def ask_server(default: str = "http://localhost:3000") -> str:
    return ask("Server URL", default=default).rstrip("/")


def ask_source(default: str = "0") -> str:
    return ask("Camera source (webcam index or video path)", default=default)


def ask_video_or_webcam(*, webcam_default: str = "0") -> str:
    """Ask webcam vs local video file (for surveillance test runs)."""
    use_video = ask_yes_no("Test with a local video file?", default=False)
    if not use_video:
        return ask("Webcam index", default=webcam_default)
    while True:
        path = ask_required("Path to video file (e.g. videos/cats/clip.mp4)")
        p = Path(path).expanduser()
        if p.is_file():
            return str(p.resolve())
        print(f"  File not found: {p}", file=sys.stderr)


def ask_access_key() -> str:
    return ask_required("Camera access key (from dashboard)")


def ask_enroll_key() -> str:
    return ask_required("User enroll key (dashboard → Users → create user)")


def ask_yes_no(label: str, *, default: bool = False) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        value = ask(f"{label} ({suffix})", default="y" if default else "n").lower()
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("  Enter y or n", file=sys.stderr)
