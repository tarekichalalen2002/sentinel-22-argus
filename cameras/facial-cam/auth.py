"""Admin username/password gate for enrollment."""

from __future__ import annotations

import getpass
import hashlib
import hmac
import sys
from pathlib import Path

import yaml

DEFAULT_CREDENTIALS = Path(__file__).resolve().parent / "credentials.yaml"
PBKDF2_ITERATIONS = 120_000


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()


def load_credentials(path: str | Path | None = None) -> dict:
    cred_path = Path(path) if path else DEFAULT_CREDENTIALS
    if not cred_path.is_file():
        raise FileNotFoundError(
            f"Credentials file not found: {cred_path}\n"
            "Create facial-cam/credentials.yaml (see auth.py defaults)."
        )
    with cred_path.open(encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    users = data.get("users") or {}
    if not users:
        raise ValueError(f"No users defined in {cred_path}")
    return users


def verify_user(username: str, password: str, users: dict) -> bool:
    record = users.get(username)
    if not record:
        return False
    salt = str(record.get("salt", ""))
    expected = str(record.get("password_hash", ""))
    if not salt or not expected:
        return False
    actual = hash_password(password, salt)
    return hmac.compare_digest(actual, expected)


def require_admin(*, credentials_path: str | Path | None = None) -> str:
    """Ask for admin username/password in the terminal, then verify."""
    try:
        users = load_credentials(credentials_path)
    except (FileNotFoundError, ValueError) as exc:
        print(exc, file=sys.stderr)
        raise SystemExit(1) from exc

    print("Admin login required to enroll.", file=sys.stderr)
    user = input("Admin username: ").strip()
    pwd = getpass.getpass("Admin password: ")

    if not user or not pwd:
        print("Username and password are required.", file=sys.stderr)
        raise SystemExit(1)

    if not verify_user(user, pwd, users):
        print("Authentication failed.", file=sys.stderr)
        raise SystemExit(1)

    print(f"Authenticated as {user}", file=sys.stderr)
    return user
