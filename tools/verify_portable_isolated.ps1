$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$verify='F:\AILAB\FB-MULTIENGINE-DOWNLOADER\verification-20261120-mission002\final-isolation'
if (Test-Path -LiteralPath (Join-Path $verify 'portable')) { throw 'Use a fresh verification directory; existing results preserved' }
New-Item -ItemType Directory -Force $verify | Out-Null
Copy-Item -LiteralPath (Join-Path $root 'dist/windows/FBMD') -Destination (Join-Path $verify 'portable') -Recurse
$executable=Join-Path $verify 'portable/FBMD.exe'
$venv=[System.IO.Path]::GetFullPath((Join-Path $root '.venv'))
$hidden=[System.IO.Path]::GetFullPath((Join-Path $root '.venv-hidden-verification'))
foreach ($path in @($venv,$hidden)) {
    if (-not $path.StartsWith([System.IO.Path]::GetFullPath($root)+[System.IO.Path]::DirectorySeparatorChar,[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe isolation path' }
}
if (Test-Path -LiteralPath $hidden) { throw 'Previous environment isolation directory exists; preserve it' }
$originalPath=$env:PATH
$originalPythonPath=$env:PYTHONPATH
$originalNative=$env:FBMD_FFMPEG
$originalState=$env:FBMD_STATE
$originalMedia=$env:FBMD_MEDIA
$checks=[ordered]@{}
function Run-Check([string]$Name,[string[]]$Arguments) {
    $report=Join-Path $verify ($Name+'.json')
    $proc=Start-Process -FilePath $executable -ArgumentList (@('--report',$report)+$Arguments) -WorkingDirectory $verify -WindowStyle Hidden -PassThru -Wait
    if ($proc.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $report)) { throw "$Name failed with exit $($proc.ExitCode)" }
    $checks[$Name]=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
}
try {
    Move-Item -LiteralPath $venv -Destination $hidden
    $env:PATH=Join-Path $env:SystemRoot 'System32'
    Remove-Item Env:PYTHONPATH,Env:PYTHONHOME,Env:FBMD_FFMPEG -ErrorAction SilentlyContinue
    $env:FBMD_STATE=Join-Path $verify 'state'
    $env:FBMD_MEDIA=Join-Path $verify 'media'
    Run-Check 'engines' @('engines')
    Run-Check 'native' @('native-test',(Join-Path $verify 'native-fixture'))
    Run-Check 'gui' @('gui-check',(Join-Path $verify 'gui-render'))
    Run-Check 'facebook' @('download','https://www.facebook.com/reel/1195289147628387')
    Run-Check 'reopened' @('download','https://www.facebook.com/reel/1195289147628387')
    if (@($checks.facebook.jobs).Count -ne 1 -or $checks.facebook.jobs[0].status -ne 'complete') { throw 'Real download did not complete' }
    if (@($checks.reopened.jobs).Count -ne 1 -or $checks.reopened.jobs[0].sha256 -ne $checks.facebook.jobs[0].sha256) { throw 'Restart or duplicate check failed' }
    $runtime=$checks.engines.engines[0]
    if ($runtime.status -ne 'READY' -or $runtime.source -ne 'bundled' -or -not $runtime.path.StartsWith((Join-Path $verify 'portable'))) { throw 'Wrong native runtime selected' }
    [ordered]@{status='PASS';source_venv_physically_unavailable=$true;path_used=$env:PATH;application=$executable;executable_sha256=(Get-FileHash -LiteralPath $executable -Algorithm SHA256).Hash.ToLowerInvariant();checks=$checks} | ConvertTo-Json -Depth 18 | Set-Content -LiteralPath (Join-Path $root 'evidence/portable-isolation.json') -Encoding utf8
} finally {
    if (Test-Path -LiteralPath $hidden) { Move-Item -LiteralPath $hidden -Destination $venv }
    $env:PATH=$originalPath
    $env:PYTHONPATH=$originalPythonPath
    $env:FBMD_FFMPEG=$originalNative
    $env:FBMD_STATE=$originalState
    $env:FBMD_MEDIA=$originalMedia
}
Write-Output 'ISOLATED_PORTABLE_ACCEPTANCE_PASS'
