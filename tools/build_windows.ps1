$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    & .venv/Scripts/python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name FBMD --paths src --collect-all yt_dlp --collect-all playwright --collect-all selenium --copy-metadata requests --copy-metadata cryptography --copy-metadata platformdirs --copy-metadata yt-dlp --copy-metadata playwright --copy-metadata selenium --copy-metadata PySide6 --exclude-module tkinter --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtQml --distpath dist/windows --workpath build/windows --specpath build tools/desktop_entry.py
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed' }
    Copy-Item -LiteralPath README.md,LICENSE -Destination dist/windows/FBMD
    & .venv/Scripts/python.exe tools/package_notices.py dist/windows/FBMD
    if ($LASTEXITCODE -ne 0) { throw 'Notice collection failed' }
} finally { Pop-Location }
