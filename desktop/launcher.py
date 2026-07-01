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


def _pick_free_port() -> int:
  with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((HOST, 0))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return int(sock.getsockname()[1])


def _helper_candidates() -> list[Path]:
  candidates: list[Path] = []
  if getattr(sys, "frozen", False):
    macos_dir = Path(sys.executable).resolve().parent
    candidates.append(macos_dir / HELPER_NAME)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
      candidates.append(Path(meipass) / HELPER_NAME)
      candidates.append(Path(meipass) / "helpers" / HELPER_NAME)
  else:
    candidates.append(Path(__file__).resolve().with_name("icloudpd_runner.py"))
  return candidates


def _resolve_helper() -> Path:
  for candidate in _helper_candidates():
    if candidate.exists():
      return candidate
  looked = "\n".join(str(path) for path in _helper_candidates())
  raise FileNotFoundError(
    "icloudpd helper executable is missing. Checked:\n" + looked
  )


class DesktopBackend:
  def __init__(self) -> None:
    self.port = _pick_free_port()
    self.url = f"http://{HOST}:{self.port}"
    self.helper_path = _resolve_helper()
    self.server = uvicorn.Server(
      uvicorn.Config(
        create_app(
          data_dir=DATA_DIR,
          authenticator=Authenticator(password_hash=None),
          session_secret=secrets.token_urlsafe(32),
          icloudpd_argv=self._icloudpd_argv,
        ),
        host=HOST,
        port=self.port,
        log_level="info",
        access_log=False,
      )
    )
    self.thread = threading.Thread(target=self.server.run, daemon=True)
    self._stopped = False

  def _icloudpd_argv(self, argv_tail: list[str]) -> list[str]:
    helper = self.helper_path
    if helper.suffix == ".py":
      return [sys.executable, str(helper), *argv_tail]
    return [str(helper), *argv_tail]

  def start(self) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    self.thread.start()
    self._wait_until_ready()

  def stop(self) -> None:
    if self._stopped:
      return
    self._stopped = True
    self.server.should_exit = True
    self.thread.join(timeout=5)

  def _wait_until_ready(self, timeout: float = 20.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
      try:
        with urllib.request.urlopen(f"{self.url}/auth/status", timeout=1) as resp:
          if resp.status == 200:
            return
      except Exception:
        time.sleep(0.2)
    raise RuntimeError("Timed out while waiting for the local web server")


def _error_html(exc: BaseException) -> str:
  details = html.escape("".join(traceback.format_exception_only(type(exc), exc)).strip())
  return f"""<!doctype html>
<html>
  <body style=\"font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 32px; line-height: 1.5;\">
    <h2 style=\"margin-top: 0;\">{APP_TITLE} failed to start</h2>
    <p>The desktop wrapper could not boot the local service.</p>
    <pre style=\"white-space: pre-wrap; background: #f4f4f4; padding: 16px; border-radius: 12px;\">{details}</pre>
    <p>Rebuild the app bundle and make sure the helper executable is included.</p>
  </body>
</html>
"""


def main() -> int:
  try:
    backend = DesktopBackend()
    atexit.register(backend.stop)
    backend.start()
  except Exception as exc:
    webview.create_window(APP_TITLE, html=_error_html(exc), width=760, height=420)
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
