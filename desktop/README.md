# macOS Desktop Wrapper

This folder packages `icloudpd-web` as a native macOS app that embeds the existing web UI in a `pywebview` window.

## Files

- `launcher.py`: Starts the local FastAPI and `uvicorn` server, then opens the desktop window.
- `icloudpd_runner.py`: Helper executable used by the app to invoke `icloudpd` commands.
- `requirements.txt`: Desktop-only build dependencies.
- `build_macos_app.sh`: Builds the helper binary and the `.app` bundle with PyInstaller.

## Build

```bash
cd /path/to/icloudpd-web
bash desktop/build_macos_app.sh
```

## Output

- `dist/iCloudPD Web.app`
- `dist/icloudpd-helper`

## Notes

- The embedded server binds to `127.0.0.1` only.
- Desktop state is stored in `~/.icloudpd-web-desktop`.
- The desktop wrapper disables the web password prompt because the UI is local-only.
- For development, run `python desktop/launcher.py`.
