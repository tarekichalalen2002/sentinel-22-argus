"""HTTP client for pairing cameras with the Sentinel server."""

from __future__ import annotations

import base64
import json
import platform
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import urllib.error
import urllib.request

DEFAULT_SERVER = "http://localhost:3000"
TOKENS_DIR = Path(__file__).resolve().parents[1] / ".tokens"


class SentinelClientError(RuntimeError):
    def __init__(self, message: str, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class SentinelClient:
    """Claim a camera access key, then call enrolled camera APIs with Bearer JWT."""

    def __init__(
        self,
        base_url: str = DEFAULT_SERVER,
        *,
        token_name: str = "camera",
        token: str | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token_path = TOKENS_DIR / f"{token_name}.json"
        self.token = token
        self.camera: dict[str, Any] | None = None
        if self.token is None:
            self._load_token()

    def _load_token(self) -> None:
        if not self.token_path.is_file():
            return
        try:
            data = json.loads(self.token_path.read_text(encoding="utf-8"))
            self.token = data.get("token")
            self.camera = data.get("camera")
            saved_url = data.get("base_url")
            if saved_url:
                self.base_url = saved_url.rstrip("/")
        except (OSError, json.JSONDecodeError):
            pass

    def _save_token(self, token: str, camera: dict[str, Any] | None) -> None:
        TOKENS_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "base_url": self.base_url,
            "token": token,
            "camera": camera,
        }
        self.token_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.token = token
        self.camera = camera

    def clear_token(self) -> None:
        self.token = None
        self.camera = None
        if self.token_path.is_file():
            self.token_path.unlink()

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        auth: bool = True,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if auth:
            if not self.token:
                raise SentinelClientError("Camera is not registered — claim an access key first")
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                parsed = {"message": raw}
            msg = parsed.get("message") or f"HTTP {exc.code}"
            raise SentinelClientError(msg, status=exc.code, body=parsed) from exc
        except urllib.error.URLError as exc:
            raise SentinelClientError(
                f"Cannot reach Sentinel server at {self.base_url}: {exc.reason}"
            ) from exc

    def claim(self, access_key: str, device_info: str | None = None) -> dict[str, Any]:
        info = device_info or f"{platform.node()} / {platform.system()} {platform.release()}"
        data = self._request(
            "POST",
            "/api/cameras/claim",
            body={"accessKey": access_key.strip(), "deviceInfo": info},
            auth=False,
        )
        token = data.get("token")
        if not token:
            raise SentinelClientError("Server did not return a camera token")
        self._save_token(token, data.get("camera"))
        print(
            f"Camera registered: {data.get('camera', {}).get('name')} "
            f"({data.get('camera', {}).get('type')}) → {self.token_path}",
            file=sys.stderr,
        )
        return data

    def session(self) -> dict[str, Any]:
        """Hit the server — fails with 401 if the camera was revoked/deleted."""
        data = self._request("GET", "/api/cameras/me")
        if data.get("camera"):
            self.camera = data["camera"]
            # Keep token file in sync with latest status from server.
            if self.token:
                self._save_token(self.token, self.camera)
        return data

    def require_active(self, *, offer_reregister: bool = False) -> dict[str, Any]:
        """Use a saved token only if the server still marks the camera active.

        For enroll/run, pass offer_reregister=False (default): silently reuse a
        valid camera session and only ask for a camera access key if needed.
        For claim, pass offer_reregister=True to optionally replace the pairing.
        """
        from common.prompts import ask_access_key, ask_yes_no

        if self.token:
            try:
                self.session()
                cam = self.camera or {}
                print(
                    f"Camera online: {cam.get('name', 'camera')} "
                    f"(status={cam.get('status')})",
                    file=sys.stderr,
                )
                if offer_reregister and ask_yes_no(
                    "Re-register this camera with a new access key?",
                    default=False,
                ):
                    self.clear_token()
                else:
                    return cam
            except SentinelClientError as exc:
                print(
                    f"Camera pairing invalid: {exc}\n"
                    "This device must be paired again with a camera access key "
                    "(dashboard → Cameras).",
                    file=sys.stderr,
                )
                self.clear_token()

        print(
            "Pair this facial/surveillance camera first (access key from Cameras).",
            file=sys.stderr,
        )
        self.claim(ask_access_key())
        return self.camera or {}

    def ensure_registered(
        self,
        access_key: str | None = None,
        *,
        prompt: bool = True,
    ) -> None:
        if self.token:
            try:
                self.session()
                return
            except SentinelClientError:
                self.clear_token()
        key = access_key
        if not key and prompt:
            from common.prompts import ask_access_key

            key = ask_access_key()
        if not key:
            raise SentinelClientError("Access key required to register this camera")
        self.claim(key)

    def gallery(self) -> list[dict[str, Any]]:
        data = self._request("GET", "/api/enroll/gallery")
        return list(data.get("users") or [])

    def enroll(
        self,
        enroll_key: str,
        *,
        face_image_b64: str | None = None,
        embedding: list[float] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"enrollKey": enroll_key.strip()}
        if face_image_b64:
            body["faceImage"] = face_image_b64
        if embedding is not None:
            body["embedding"] = embedding
        return self._request("POST", "/api/enroll", body=body)

    def verify(self, username: str) -> dict[str, Any]:
        return self._request("POST", "/api/enroll/verify", body={"username": username})

    def post_alert(
        self,
        *,
        category: str,
        label: str = "",
        confidence: float = 0.0,
        box: tuple[int, int, int, int] | None = None,
        snapshot_b64: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "category": category,
            "label": label,
            "confidence": float(confidence),
        }
        if box is not None:
            x, y, w, h = box
            body["box"] = {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
        if snapshot_b64:
            body["snapshot"] = snapshot_b64
        return self._request("POST", "/api/alerts", body=body)


def bgr_to_jpeg_b64(bgr: np.ndarray, quality: int = 85) -> str:
    ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError("Failed to encode JPEG")
    return base64.b64encode(buf.tobytes()).decode("ascii")


def jpeg_b64_to_bgr(data: str) -> np.ndarray | None:
    raw = data
    if "," in raw and raw.strip().startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        arr = np.frombuffer(base64.b64decode(raw), dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except Exception:
        return None
