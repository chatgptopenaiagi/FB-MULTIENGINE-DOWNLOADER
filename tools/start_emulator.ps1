$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot -Parent
$env:ANDROID_HOME=Join-Path $root '.toolchain/android-sdk'
$env:ANDROID_SDK_ROOT=$env:ANDROID_HOME
$env:ANDROID_AVD_HOME=Join-Path $root '.toolchain/avd'
$avd=Join-Path $env:ANDROID_AVD_HOME 'FBMD_API30.avd'
New-Item -ItemType Directory -Path $avd -Force | Out-Null
@"
avd.ini.encoding=UTF-8
path=$avd
target=android-30
"@ | Set-Content -LiteralPath (Join-Path $env:ANDROID_AVD_HOME 'FBMD_API30.ini') -Encoding ascii
@"
AvdId=FBMD_API30
avd.ini.displayname=FBMD API30 isolated verification
abi.type=x86_64
hw.cpu.arch=x86_64
hw.cpu.ncore=2
hw.ramSize=2048
hw.lcd.width=720
hw.lcd.height=1280
hw.lcd.density=320
hw.keyboard=yes
hw.gpu.enabled=yes
hw.gpu.mode=swiftshader_indirect
hw.audioInput=no
disk.dataPartition.size=2G
image.sysdir.1=$env:ANDROID_HOME\system-images\android-30\google_apis\x86_64\
tag.id=google_apis
tag.display=Google APIs
PlayStore.enabled=false
showDeviceFrame=no
fastboot.forceColdBoot=yes
"@ | Set-Content -LiteralPath (Join-Path $avd 'config.ini') -Encoding ascii
$proc=Start-Process -FilePath (Join-Path $env:ANDROID_HOME 'emulator/emulator.exe') -ArgumentList '-avd','FBMD_API30','-port','5556','-no-window','-no-audio','-no-boot-anim','-no-snapshot','-gpu','swiftshader_indirect' -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root '.private/emulator.log') -RedirectStandardError (Join-Path $root '.private/emulator-error.log')
Write-Output "Emulator PID: $($proc.Id)"
