[Setup]
AppId={{67BDB28C-9C8E-4D1E-80AB-B0FB5B744244}
AppName=FB MultiEngine Downloader
AppVersion=0.2.0-alpha.1
AppPublisher=chatgptopenaiagi
AppPublisherURL=https://github.com/chatgptopenaiagi/FB-MULTIENGINE-DOWNLOADER
DefaultDirName={localappdata}\Programs\FBMultiEngine
DefaultGroupName=FB MultiEngine Downloader
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\release
OutputBaseFilename=FBMD-0.2.0-alpha.1-windows-x64-setup
Compression=lzma2/fast
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\FBMD.exe
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes

[Files]
Source: "..\dist\windows\FBMD\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FB MultiEngine Downloader"; Filename: "{app}\FBMD.exe"
Name: "{group}\Uninstall FB MultiEngine Downloader"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\FBMD.exe"; Description: "Launch FB MultiEngine Downloader"; Flags: nowait postinstall skipifsilent

; No UninstallDelete entries: personal state and media are outside {app} and preserved.
