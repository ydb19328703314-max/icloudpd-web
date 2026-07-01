#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv-desktop"
DIST_DIR="$ROOT_DIR/dist"
BUILD_DIR="$ROOT_DIR/build"
HELPER_NAME="icloudpd-helper"
APP_NAME="iCloudPD Web"

python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip setuptools wheel
python -m pip install -e "$ROOT_DIR"
python -m pip install -r "$ROOT_DIR/desktop/requirements.txt"

rm -rf "$BUILD_DIR" "$DIST_DIR"

pyinstaller --noconfirm --clean --onefile --name "$HELPER_NAME" "$ROOT_DIR/desktop/icloudpd_runner.py"

HELPER_BIN="$DIST_DIR/$HELPER_NAME"
chmod +x "$HELPER_BIN"

pyinstaller --noconfirm --clean --windowed --name "$APP_NAME" --collect-data icloudpd_web --hidden-import webview.platforms.cocoa --add-binary "$HELPER_BIN:." "$ROOT_DIR/desktop/launcher.py"

echo
echo "Built app bundle: $DIST_DIR/$APP_NAME.app"
echo "Bundled helper: $HELPER_BIN"
