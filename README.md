# FB MultiEngine Downloader

An independent local media downloader for Windows, Android and Python. Alpha release: **0.1.0-alpha.1**. The release verification report is the authority for tested capabilities and current Facebook access limits.

## What it does

- Windows: PySide6 interface, visible-link discovery with Playwright or Selenium, HTTP and yt-dlp downloads, persistent queue/history, pause/resume, cancellation, content hashes and duplicate prevention.
- Android: Kotlin/Compose UI, native on-device HTTP and yt-dlp downloads, foreground service, SQLite queue, Android Keystore and Storage Access Framework export. Progressive audio/video formats only; profile discovery and browser-session extraction are desktop-only.
- Python: installable wheel, `fbmd` CLI and typed `fbmd.client.Downloader` API. Optional authenticated loopback API; remote downloader services and LAN listening are disabled.

Access restrictions stop processing. The app does not defeat authentication, CAPTCHA, account restrictions or private-content permissions. Only save media you are permitted to archive.

## Windows

Extract the entire portable ZIP and launch `FBMD.exe`. Keep `_internal` alongside it. No Python installation is needed. Media defaults to `F:\AILAB\FB-MULTIENGINE-DOWNLOADER` when that drive is available, otherwise your Downloads folder. Choose another destination in Settings.

Paste video URLs on Home, add them, then press Start. Sources scans profile/Page URLs; Index only is enabled initially. Accounts requires explicit consent before saving a dedicated browser session. Existing browser profiles are never read automatically.

Microsoft Edge is used when installed. The wheel can install Chromium with `python -m playwright install chromium`. FFmpeg is an optional separately installed executable: select it in Settings or set `FBMD_FFMPEG`. Without it, progressive formats are selected. With it, yt-dlp may merge separate streams and completed video files undergo a decode check.

## Python

```powershell
python -m pip install .\fb_multiengine_downloader-0.1.0a1-py3-none-any.whl
fbmd doctor
fbmd add "https://www.facebook.com/reel/VIDEO_ID"
fbmd run
fbmd list
fbmd pause
fbmd resume
fbmd export manifest.json
```

For browser discovery: `pip install "fb-multiengine-downloader[browser]"` after the package is available in your package source, or install `playwright selenium` directly. Use `fbmd discover "PROFILE_URL" --rounds 20 --enqueue`. Without `--enqueue`, discovery is index-only. Use `fbmd login --save-session` to explicitly save the dedicated browser session. `--state`, `--media` and `--account` precede the subcommand.

```python
from fbmd.client import Downloader
app = Downloader("./local-state", "./media")
app.enqueue("https://example.org/authorized-media.mp4")
results = app.run()
```

On Linux/macOS, a secure OS keyring is required; these platforms have not been release-tested in this mission.

## Android

Install the APK from the verified release. Share a video URL to FB MultiEngine or paste it, add it, and tap Start. Downloads stay on the device. Use Save to folder to copy completed files to a location selected through Android's system picker. Internal app files are removed on uninstall; export them first. No desktop service is required.

The universal package contains ARM64 and x86_64 native libraries. Check the verification report for the exact emulator/device architecture tested. A physical ARM64 device is not assumed available.

## API and credentials

Install the `api` extra or `fastapi uvicorn`, then run `fbmd serve`. It binds only to `127.0.0.1:8765`. Every endpoint requires a Bearer token; `fbmd api-token --reveal` explicitly displays the generated local token. The token is otherwise encrypted. An authenticated `/openapi.json` describes the contract. Do not expose this alpha through a reverse proxy.

Windows credentials use Fernet encryption with the key protected by current-user DPAPI. Android uses AES-GCM with Android Keystore. URLs containing signed query parameters are encrypted in the queue. Exports omit query strings and all credential values. Each Windows account label has separate state and credentials. No password collection or Meta App Secret storage is implemented.

Meta integration can probe an existing authorized token and explicitly supplied object. OAuth requires a configured, reviewed app and is unavailable here. The current `video_reels` reference does not support reads. See [Meta limits](docs/META_API.md) and [research](docs/ENGINE_RESEARCH.md).

## Limits and evidence

Discovery is bounded and coverage is uncertain. Facebook changes may break extractors independently of the local download engine. Successful generated-media tests are not proof of live Facebook compatibility. Unknown metadata is not fabricated. Date/duration filters, Android DASH merging, OAuth onboarding, automatic LAN pairing and global cross-account concurrency are not implemented in this alpha.

See [build instructions](docs/BUILD.md), [architecture and recovery](docs/ARCHITECTURE.md), [security](docs/SECURITY.md), and [verification](evidence/VERIFICATION.md). Release assets include SHA-256 checksums. Keep session state, downloaded media and signing keys out of source control.
