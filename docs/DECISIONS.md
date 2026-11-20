# Engineering decision log

- Mission 001: retain existing project and media; install build tools in scoped directories. Use one session, without delegated agents.
- Use a shared Python engine for Windows/wheel and a real native Android service; reject hosted download wrappers and unsupported access workarounds.
- Use SQLite WAL, encrypted original URLs and OS-backed credentials; fix range handling and preserve unknown existing files with checksum receipts.
- Replace legacy Android instrumentation runner with AndroidX; retain successful runtime HTTP/pause/resume/native extraction checks.
- Android release lint found test-only cleartext domains. Move those to debug configuration; release requires HTTPS.
- Windows interactive test overlapped manual sign-in activity. Preserve the operator's session, use separate acceptance state and targeted accessibility actions. Do not publish screenshots of unrelated windows.
- Mission 001 baseline: 32 Python tests, Android instrumentation, all three installed-package real Reel downloads, and an opt-in authenticated profile scan yielding 73 links plus two successful downloads. Preserve baseline binaries before Mission 002.
- Mission 002: integrate a verified FFmpeg/FFprobe bundle and internal registry, test native dependencies, add portable and installer acceptance, preserve prior queue/vault schemas and user data.
- Select the upstream LGPL shared Windows build and retain its exact dependency closure. Its Schannel HTTPS support uses Windows cryptography; unrelated DLL collections are unnecessary. Frozen execution never silently falls back to PATH.
- Bundle the Playwright Chromium revision and matching ChromeDriver. Both discovery engines were exercised from the independent portable app with the explicitly saved session.
- Separate Android debug application ID from release so instrumented tests cannot uninstall release data. Retain only the FFmpeg executable closure, resolving ZIP symlinks. An initial pruning failure omitted the upstream libandroid compatibility stub; loading the OS library then conflicted with liblzma. Retaining the stub and matching the extractor's library order repaired the actual runtime failure; retests passed.
- Use a per-user Inno Setup installer containing the complete portable tree. Test installation, upgrade and uninstallation against dedicated state/media. No personal data deletion rules are included.
- Publish a partial alpha with explicit physical-ARM64, 16 KB alignment, Meta OAuth and long-video limits. Static ABI checks never stand in for execution.
