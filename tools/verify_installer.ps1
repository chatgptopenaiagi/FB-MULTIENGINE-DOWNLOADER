$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$verify='F:\AILAB\FB-MULTIENGINE-DOWNLOADER\verification-20261120-mission002\installer-test-release'
if (Test-Path -LiteralPath $verify) { throw 'Existing installer evidence must be preserved; choose a fresh directory' }
New-Item -ItemType Directory $verify | Out-Null
$program=Join-Path $verify 'program'
$installer=Join-Path $root 'dist/release/FBMD-0.2.0-alpha.1-windows-x64-setup.exe'
$group='FB MultiEngine Downloader'
$checks=[ordered]@{}
function Install-Test {
    $p=Start-Process -FilePath $installer -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR="'+$program+'"'),('/GROUP="'+$group+'"'),('/LOG="'+(Join-Path $verify 'install.log')+'"')) -WindowStyle Hidden -PassThru -Wait
    if ($p.ExitCode -ne 0) { throw "Installer exit $($p.ExitCode)" }
}
function Run-Check([string]$Name,[string[]]$Arguments) {
    $report=Join-Path $verify ($Name+'.json')
    $p=Start-Process -FilePath (Join-Path $program 'FBMD.exe') -ArgumentList (@('--report',$report)+$Arguments) -WorkingDirectory $verify -WindowStyle Hidden -PassThru -Wait
    if ($p.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $report)) { throw "$Name failed" }
    $checks[$Name]=Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
}
$saved=@{}
foreach($name in @('PATH','PYTHONPATH','PYTHONHOME','FBMD_FFMPEG','FBMD_STATE','FBMD_MEDIA')) { $saved[$name]=[Environment]::GetEnvironmentVariable($name) }
try {
    $env:PATH=Join-Path $env:SystemRoot 'System32'
    Remove-Item Env:PYTHONPATH,Env:PYTHONHOME,Env:FBMD_FFMPEG -ErrorAction SilentlyContinue
    $env:FBMD_STATE=Join-Path $verify 'state'
    $env:FBMD_MEDIA=Join-Path $verify 'media'
    Install-Test
    $shortcut=Join-Path ([Environment]::GetFolderPath('StartMenu')) ('Programs\'+$group+'\FB MultiEngine Downloader.lnk')
    if (-not (Test-Path -LiteralPath $shortcut)) { throw 'Start Menu shortcut missing' }
    Run-Check 'engines' @('engines')
    Run-Check 'native' @('native-test',(Join-Path $verify 'native-fixture'))
    Run-Check 'gui' @('gui-check',(Join-Path $verify 'gui-render'))
    Run-Check 'facebook' @('download','https://www.facebook.com/reel/1195289147628387')
    if ($checks.facebook.jobs[0].status -ne 'complete') { throw 'Download failed' }
    $media=$checks.facebook.jobs[0].path
    $hash=(Get-FileHash -LiteralPath $media -Algorithm SHA256).Hash
    Install-Test
    Run-Check 'reopened_after_upgrade' @('download','https://www.facebook.com/reel/1195289147628387')
    if (@($checks.reopened_after_upgrade.jobs).Count -ne 1 -or (Get-FileHash -LiteralPath $media -Algorithm SHA256).Hash -ne $hash) { throw 'Upgrade changed history or media' }
    $database=Join-Path $env:FBMD_STATE 'queue.sqlite3'
    if (-not (Test-Path -LiteralPath $database)) { $database=@(Get-ChildItem -LiteralPath $env:FBMD_STATE -Filter '*.sqlite*')[0].FullName }
    $dbHash=(Get-FileHash -LiteralPath $database -Algorithm SHA256).Hash
    $p=Start-Process -FilePath (Join-Path $program 'unins000.exe') -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART') -WindowStyle Hidden -PassThru -Wait
    if ($p.ExitCode -ne 0 -or (Test-Path -LiteralPath (Join-Path $program 'FBMD.exe')) -or (Test-Path -LiteralPath $shortcut)) { throw 'Uninstallation failed' }
    if ((Get-FileHash -LiteralPath $media -Algorithm SHA256).Hash -ne $hash -or (Get-FileHash -LiteralPath $database -Algorithm SHA256).Hash -ne $dbHash) { throw 'Uninstall changed personal data' }
    [ordered]@{status='PASS';installer_sha256=(Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant();path_used=$env:PATH;start_menu='PASS';upgrade_preserved_history='PASS';uninstall_preserved_database_and_media='PASS';checks=$checks} | ConvertTo-Json -Depth 18 | Set-Content -LiteralPath (Join-Path $root 'evidence/installer-verification.json') -Encoding utf8
} finally { foreach($name in $saved.Keys) { [Environment]::SetEnvironmentVariable($name,$saved[$name]) } }
Write-Output 'INSTALLER_ACCEPTANCE_PASS'
