# 0.2.0-alpha.1 — integrated native engines

Windows now ships its own verified FFmpeg/FFprobe, matching multimedia DLLs, Python/Qt runtime, yt-dlp, Chromium and ChromeDriver. Extract the complete portable ZIP and run FBMD.exe, or use the per-user installer. No separate Python/FFmpeg installation or PATH configuration is needed. The Native Engine Control panel reports versions, architecture, source, operational state and capabilities after probing the executables.

The persistent queue retains pause/resume, retry/backoff, crash recovery, duplicate checks, encrypted credentials and access boundaries. Native processing adds split audio/video merging, HLS processing, codec/container inspection and decode verification. All media processing is local. Windows installer upgrade/uninstall preserves personal databases and media.

The updated Android APK contains ARM64 and x86_64 Python/extractor/media runtimes. Its startup fixture must successfully merge, inspect and decode audio/video before native capability is READY. The Python wheel supports explicit checksum-pinned Windows native provisioning with `fbmd provision-native`.

## Downloads

- **FBMD-0.2.0-alpha.1-windows-x64.zip** — complete portable Windows application.
- **FBMD-0.2.0-alpha.1-windows-x64-setup.exe** — installer with Start Menu entry and uninstaller.
- **FBMD-0.2.0-alpha.1-android-arm64-x86_64.apk** — signed universal APK; execution tested on x86_64 Android 11.
- **fb_multiengine_downloader-0.2.0a1-py3-none-any.whl** — Python 3.11+ CLI/reusable engine.
- **FBMD-0.2.0-alpha.1-native-windows-x64.zip** — pinned upstream native archive retained for wheel provisioning.
- **FBMD-0.2.0-alpha.1-sources.zip** — application source, upstream native sources, build recipes and source/checksum manifests.
- **FBMD-0.2.0-alpha.1-evidence.zip**, **verification.json**, **SHA256SUMS.txt** — acceptance evidence and artifact checksums.

## Verification

35 Python regression tests passed. The portable app ran outside the source tree while the development venv was unavailable and PATH contained only Windows system tools. Bundled FFmpeg merged synthetic separate audio/video streams, passed FFprobe track/duration checks and full decode, processed HLS, and completed yt-dlp split-format merging. Both bundled browser discovery engines worked from the packaged application. The installer passed install, GUI/media, upgrade/reopen/deduplication and uninstall preservation checks.

A permitted public Reel downloaded on Windows and Android with VP9 720×1280 video and AAC audio. Android exported its locally downloaded file through the system folder picker. The installed wheel independently downloaded a public Reel and exercised native provisioning/processing. Static inspection covered 155 Windows PE binaries and 438 Android ELF objects with no unresolved required imports. Exact sources, methods, hashes and runtime scope appear in [the verification report](https://github.com/chatgptopenaiagi/FB-MULTIENGINE-DOWNLOADER/blob/main/evidence/VERIFICATION.md).

## Known limits

This is a **verified partial alpha**, not a claim that every source/device is supported. Physical ARM64 execution was unavailable; ARM64 receives static ABI/dependency checks only. Some Android libraries have less than 16 KB segment alignment, so 16 KB device compatibility is not certified. Meta authenticated Graph access/OAuth onboarding and long-video success remain unverified. Profile discovery is bounded and does not prove completeness. Access restrictions are honored. Date/duration filters, LAN pairing and Android browser-session discovery are not implemented. Windows binaries are unsigned; the APK uses the project's private release key.

No downloaded Facebook media, credentials, session cookies, local databases or signing secrets are included. This software uses FFmpeg under its applicable LGPL/GPL terms; source and notices accompany the release. Original Windows/Python code is MIT; Android integration is GPL-3.0. See [third-party notices](https://github.com/chatgptopenaiagi/FB-MULTIENGINE-DOWNLOADER/blob/main/docs/THIRD_PARTY.md).
