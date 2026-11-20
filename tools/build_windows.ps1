$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    & .venv/Scripts/python.exe tools/provision_native.py
    if ($LASTEXITCODE -ne 0) { throw 'Native provisioning failed' }
    if (-not (Test-Path -LiteralPath .toolchain/playwright)) { throw 'Provision bundled Chromium first (PLAYWRIGHT_BROWSERS_PATH=.toolchain/playwright)' }
    & .venv/Scripts/python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name FBMD --paths src --collect-all yt_dlp --collect-all playwright --collect-all selenium --copy-metadata requests --copy-metadata cryptography --copy-metadata platformdirs --copy-metadata yt-dlp --copy-metadata playwright --copy-metadata selenium --copy-metadata PySide6 --exclude-module tkinter --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtQml --distpath dist/windows --workpath build/windows --specpath build tools/desktop_entry.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
    # The matching bundled ChromeDriver is used directly; omit unused manager binaries.
    $packageRoot=[System.IO.Path]::GetFullPath((Join-Path $PWD 'dist/windows/FBMD'))
    foreach ($platformName in @('windows','linux','macos')) {
        $unused=[System.IO.Path]::GetFullPath((Join-Path $packageRoot ('_internal/selenium/webdriver/common/'+$platformName)))
        if (-not $unused.StartsWith($packageRoot+[System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe package prune path' }
        if (Test-Path -LiteralPath $unused) { Remove-Item -LiteralPath $unused -Recurse -Force }
    }
    Copy-Item -LiteralPath README.md,LICENSE -Destination dist/windows/FBMD
    New-Item -ItemType Directory -Force dist/windows/FBMD/_internal/fbmd | Out-Null
    Copy-Item -LiteralPath src/fbmd/native-windows.lock.json -Destination dist/windows/FBMD/_internal/fbmd
    New-Item -ItemType Directory -Force dist/windows/FBMD/engines | Out-Null
    Copy-Item -LiteralPath .toolchain/native/ffmpeg -Destination dist/windows/FBMD/engines -Recurse
    New-Item -ItemType Directory -Force dist/windows/FBMD/engines/browser | Out-Null
    Get-ChildItem .toolchain/playwright -Directory -Filter 'chromium-*' | Copy-Item -Destination dist/windows/FBMD/engines/browser -Recurse
    Copy-Item -LiteralPath .toolchain/discovery -Destination dist/windows/FBMD/engines -Recurse
    Copy-Item -LiteralPath docs -Destination dist/windows/FBMD/documentation -Recurse
    New-Item -ItemType Directory -Force dist/windows/FBMD/evidence | Out-Null
    Copy-Item -LiteralPath evidence/VERIFICATION.md -Destination dist/windows/FBMD/evidence
    & .venv/Scripts/python.exe tools/package_notices.py dist/windows/FBMD
    if ($LASTEXITCODE -ne 0) { throw 'Notice collection failed' }
} finally { Pop-Location }
