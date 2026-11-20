# Reproducible build procedure

Builds use project-scoped tools. Do not reuse a production browser profile or put media/credentials into source. The release report identifies the exact tested tool versions. Repeatability means the documented source/dependency procedure; byte-identical timestamps and signing output are not promised.

## Windows and wheel

Use Windows x64 with Python 3.13 (the independent wheel test also uses 3.11), PowerShell and Git. From the project:

```powershell
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -e '.[browser,desktop,api,dev]'
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path $PWD '.toolchain/playwright'
.venv/Scripts/python.exe -m playwright install chromium --no-shell
.venv/Scripts/python.exe tools/provision_native.py
.venv/Scripts/python.exe tools/provision_chromedriver.py
.venv/Scripts/python.exe -m pytest --basetemp=.private/fresh-test-run -q
.venv/Scripts/python.exe -m ruff check src tests tools --select F
.venv/Scripts/python.exe -m build --wheel
./tools/build_windows.ps1
```

The Windows artifact is the full `dist/windows/FBMD` directory, including `_internal`, `engines`, documentation and THIRD_PARTY_LICENSES. Native provisioning verifies the pinned upstream archive checksum. Browser provisioning uses the Chromium revision required by the installed Playwright and the exact matching ChromeDriver. Compile `tools/windows-installer.iss` with Inno Setup 7 to package the same tree. Use `evidence/python-dependencies.txt` to reproduce the tested dependency set. `tools/check_native_dependencies.py` audits the final PE import closure. Installer and portable verification scripts use dedicated external directories; adapt those paths for another machine without overwriting previous evidence.

## Android

Use JDK 21, Android SDK platform 35/build-tools 35.0.0 and Gradle 8.13. AGP is 8.9.1, Kotlin 2.0.21, minimum API 26 and target API 35. `tools/bootstrap_android.py` installs project-scoped tools after checksum verification. Set JAVA_HOME, ANDROID_HOME, ANDROID_SDK_ROOT and GRADLE_USER_HOME to the scoped tools, or adapt to your existing compatible installations.

```powershell
.venv/Scripts/python.exe -m pip install pyelftools requests
.venv/Scripts/python.exe tools/prepare_android_native.py
.toolchain/gradle-8.13/bin/gradle.bat -p android assembleDebug
.toolchain/gradle-8.13/bin/gradle.bat -p android connectedDebugAndroidTest
```

The instrumented test expects tools/fixture_server.py on localhost:18765, with the generated H.264/AAC sample at `.private/fixture/sample.mp4`, and `adb reverse tcp:18765 tcp:18765`. Generate the fixture with `tools/generate_fixture.py`. Tests prove local FFmpeg merging/decoding, HTTP resume and embedded yt-dlp execution; public Facebook access is tested separately. Debug uses a distinct application ID, preserving an installed release's data. Native preparation retains executable dependencies, including the upstream Android stub library, and resolves archive symlinks into regular ELF files.

Release signing accepts environment variables FBMD_KEYSTORE, FBMD_STORE_PASSWORD and FBMD_KEY_PASSWORD with alias `fbmd`; never commit them. `tools/build_android.py` uses the local JDK/SDK paths in this mission and creates a dedicated RSA key with a DPAPI-wrapped password under `.private/signing` if none exists. Adapt paths for another machine. It builds the signed APK and runs the connected tests. Public CI builds debug APKs without release secrets. A universal APK contains arm64-v8a and x86_64; the release evidence distinguishes compiled ABIs from the architecture actually run.

## Independent acceptance and publishing

Install the wheel in a fresh venv outside the source tree and run tools/verify_installed_wheel.py from there. Copy the desktop folder outside the source tree and test the EXE through its real UI. Install the exact release APK, complete a download, relaunch and verify history, export/copy and hash the media, and check the APK signature and ABI headers. Do not count a debug test as execution of the release binary.

CI builds artifacts and records checksums. The release workflow accepts only manually verified artifacts already uploaded to a draft, checks the manifest and publishes that reviewed draft. Do not tag or publish an artifact merely because compilation succeeded. Supply verification evidence, limitations, dependency notices, corresponding source and SHA256SUMS.txt.
