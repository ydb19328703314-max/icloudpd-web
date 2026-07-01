from __future__ import annotations

import atexit
import html
import secrets
import socket
import sys
import threading
import time
import traceback
import urllib.request
from pathlib import Path

import uvicorn
import webview

from icloudpd_web.app import create_app
from icloudpd_web.auth import Authenticator

APP_TITLE = "iCloudPD Web"
HOST = "127.0.0.1"
DATA_DIR = Path.home() / ".icloudpd-web-desktop"
HELPER_NAME = "icloudpd-helper"


def pick_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, 0))
        return int(sock.getsockname()[1])


def helper_candidates() -> list[Path]:
    if getattr(sys, "frozen", False):
        paths = [Path(sys.executable).resolve().parent / HELPER_NAME]
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            base = Path(meipass)
            paths.extend([
                base / HELPER_NAME,
                base / "helpers" / HELPER_NAME,
            ])
        return paths

    return [Path(__file__).resolve().with_name("icloudpd_runner.py")]


def resolve_helper() -> Path:
    for candidate in helper_candidates():
        if candidate.exists():
            return candidate
    raise FileNotFoundError("icloudpd helper executable is missing")


class Backend:
    def __init__(self) -> None:
        self.port = pick_port()
        self.url = f"http://{HOST}:{self.port}"
        self.helper = resolve_helper()
        self.server = uvicorn.Server(
            uvicorn.Config(
                create_app(
                    data_dir=DATA_DIR,
                    authenticator=Authenticator(password_hash=None),
                    session_secret=secrets.token_urlsafe(32),
                    icloudpd_argv=self.icloudpd_argv,
                ),
                host=HOST,
                port=self.port,
                log_level="info",
                access_log=False,
            )
        )
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.stopped = False

    def icloudpd_argv(self, tail: list[str]) -> list[str]:
        if self.helper.suffix == ".py":
            return [sys.executable, str(self.helper), *tail]
        return [str(self.helper), *tail]

    def start(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.thread.start()
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(f"{self.url}/auth/status", timeout=1) as response:
                    if response.status == 200:
                        return
            except Exception:
                time.sleep(0.2)
        raise RuntimeError("Timed out while waiting for the local web server")

    def stop(self) -> None:
        if self.stopped:
            return
        self.stopped = True
        self.server.should_exit = True
        self.thread.join(timeout=5)


def error_html(exc: Exception) -> str:
    details = html.escape("".join(traceback.format_exception_only(type(exc), exc)).strip())
    return (
        "<!doctype html>"
        "<html><body style=\"font-family: -apple-system, BlinkMacSystemFont, sans-serif; "
        "padding: 32px; line-height: 1.5;\">"
        f"<h2 style=\"margin-top: 0;\">{APP_TITLE} failed to start</h2>"
        "<p>The desktop wrapper could not boot the local service.</p>"
        f"<pre style=\"white-space: pre-wrap; background: #f4f4f4; padding: 16px; border-radius: 12px;\">{details}</pre>"
        "<p>Rebuild the app bundle and make sure the helper executable is included.</p>"
        "</body></html>"
    )


def main() -> int:
    try:
        backend = Backend()
        atexit.register(backend.stop)
        backend.start()
    except Exception as exc:
        webview.create_window(APP_TITLE, html=error_html(exc), width=760, height=420)
        webview.start(gui="cocoa", debug=False)
        return 1

    window = webview.create_window(
        APP_TITLE,
        backend.url,
        width=1360,
        height=900,
        min_size=(980, 720),
    )
    window.events.closed += backend.stop

    try:
        webview.start(gui="cocoa", debug=not getattr(sys, "frozen", False))
    finally:
        backend.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
