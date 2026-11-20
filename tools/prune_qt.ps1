param([string]$Package='dist/windows/FBMD')
$ErrorActionPreference='Stop'
$root=[System.IO.Path]::GetFullPath((Join-Path (Split-Path $PSScriptRoot -Parent) $Package))
$allowed=[System.IO.Path]::GetFullPath((Join-Path (Split-Path $PSScriptRoot -Parent) 'dist/windows/FBMD'))
if ($root -ne $allowed) { throw 'Pruning is restricted to the generated Windows package' }
# Widgets-only app: PDF and virtual keyboard plugins pull in unrelated QML/Quick libraries.
$unused=@('plugins/imageformats/qpdf.dll','plugins/platforminputcontexts/qtvirtualkeyboardplugin.dll','plugins/tls/qopensslbackend.dll','Qt6Pdf.dll','Qt6VirtualKeyboard.dll','Qt6Quick.dll','Qt6Qml.dll','Qt6QmlMeta.dll','Qt6QmlModels.dll','Qt6QmlWorkerScript.dll')
foreach ($name in $unused) {
    $path=[System.IO.Path]::GetFullPath((Join-Path $root ('_internal/PySide6/'+$name)))
    if (-not $path.StartsWith($root+[System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe generated package path' }
    if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
}
