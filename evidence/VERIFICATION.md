# Mission 002 verification — 0.2.0-alpha.1

Test date: 20 November 2026. This is a verified **partial alpha**, with the limits below. Compilation, static inspection, synthetic fixtures and live-source tests are reported separately. SHA256SUMS.txt in the release identifies the exact delivered artifacts; verification.json binds the platform acceptance results to that release.

| Check | Result | Evidence |
|---|---|---|
| Python engine/security/API/native regression suite | 35 passed, 0 skipped | python-tests.xml |
| Independent Windows portable | Passed with source venv renamed away, PATH limited to Windows System32, separate state and media | portable-isolation.json |
| Bundled FFmpeg/FFprobe | Version/codec/container/protocol probes, separate video/audio merge, full decode, HLS remux, yt-dlp split-format Merger | portable-isolation.json |
| GUI | All ten pages rendered by the packaged Qt application; previous real UI enqueue/start/restart acceptance retained | windows-integrated-engines.png, windows-integrated-settings.png |
| Bundled browsers | Packaged Playwright and Selenium each discovered 10 visible links from the supplied profile using the explicitly saved app session | packaged-playwright-discovery.json, packaged-selenium-discovery.json |
| Windows installer | Silent install, Start Menu entry, GUI/media tests, reinstall, reopen/deduplication and uninstall preserving database/media | installer-verification.json |
| Windows native imports | 155 x64 PE binaries, no unresolved imports in the package/Windows dependency check | windows-native-dependencies.json |
| Android instrumentation | Local FFmpeg merge/decode, HTTP pause/range resume, embedded yt-dlp, duplicate prevention, 403 stop, vault encryption and persistence | android-instrumented-tests.xml |
| Signed Android release | Local Reel download, SAF export, reopen/reinstall duplicate check, startup FFmpeg self-test | android-release-media.json, android-native-engines.png |
| Android ABI/import inspection | 438 ELF objects, ARM64 and x86_64, no missing DT_NEEDED dependencies | android-native-dependencies.json |
| Installed wheel | Python 3.11 outside source, real download/reopen/deduplication; checksum-pinned native provisioning and multimedia fixture | wheel-verification.json, wheel-native.json |

## Live media

- `https://www.facebook.com/reel/4130607413898579/`: signed Android release downloaded and exported 6,452,353 bytes, SHA-256 `9dfabf97a07d436314a3c269db8607e60eaef3439dabd7a6b50525744f356803`. FFprobe found VP9 720×1280 and AAC stereo, duration 19.667 seconds. The independent Windows executable also downloaded this source with its own native engine: 6,452,361 bytes, SHA-256 `e3ab4bf0e4d6169fd5440dcf8cdbb689d603a6ffb6839f7621202851801e03b6`. Container bytes may differ across the two FFmpeg versions.
- `https://www.facebook.com/reel/1195289147628387`: progressive regression downloaded by all three products; 622,802 bytes, SHA-256 `cc12fd22535bfa0d5f224e105c1c4abf3525cc4cf33501d1f7ed6c5c469123a2`. Its exposed progressive file has H.264 video and **no audio**. Audio presence is not claimed for this source.
- Supplied profile `https://www.facebook.com/profile.php?id=61595152335606&sk=reels_tab`: anonymous discovery stopped at the login boundary. An explicitly saved app session subsequently yielded 73 visible links over 20 scrolls; two selected downloads had valid audio/video streams. See authenticated-profile-check.json and authenticated-media-inspection.json. Bounded discovery does not establish complete coverage.
- Two longer upstream regression URLs failed Facebook extraction under ordinary unauthenticated access. No long-video success is claimed and no access restriction was bypassed.

Downloaded Facebook media and session state remain local. Only redacted metadata, hashes and application screenshots are published. Synthetic fixtures are distinct from Facebook tests.

## Limits that remain

- ARM64 native libraries are packaged and statically inspected, but no physical ARM64 device was available. Actual APK execution and native merging were tested on an x86_64 Android 11 emulator. Some bundled ELF segments have alignment below 16 KB; compatibility with 16 KB Android devices is not certified.
- Android split-stream capability is gated by a real local FFmpeg self-test. The report does not claim every Facebook DASH/HLS variant works on every device. Desktop controlled fixtures independently exercise split-format selection/merging and HLS processing.
- Meta Graph API access requires a separately authorized app/token. Missing-token boundaries are tested; authenticated Graph/OAuth onboarding is unverified and OAuth is not implemented. API access does not grant arbitrary profile access.
- Source availability, login, permissions, expiry, rate limits and extractor changes remain external constraints. Repeated retries do not confer access. No complete-profile, long-video or universal-format guarantee is made.
- Date/duration filters, LAN pairing, global cross-account concurrency and Android browser-session discovery are not implemented. Windows executables/installers are unsigned; the APK uses the project's locally held release signing key.
- Native dependency reports are static import checks supplemented by the listed runtime tests, not certification of all possible plugins or every Windows/Android version.

Mission 001 artifacts and user data were preserved separately. The source repository contains all 41 repository assessments, architecture, manual, build steps, engine inventories and licensing/source notices.
