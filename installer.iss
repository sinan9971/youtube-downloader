; Inno Setup Script za YouTube Downloader
#define MyAppName "YouTube Downloader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "YouTube Downloader"
#define MyAppExeName "youtube_downloader.exe"

[Setup]
; Osnovne informacije o aplikaciji
AppId={{D37F619B-5147-4BEA-B561-A1DF6E243719}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes

; Ikona instalera i deinstalacije
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\icon.ico

; Izlazna datoteka
OutputDir=dist
OutputBaseFilename=YouTube_Downloader_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Dozvole
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Glavna izvršna datoteka i ikonica
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Prečac u Start izborniku
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
; Prečac na Radnoj površini (Desktop)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; Opcija za pokretanje programa nakon dovršetka instalacije
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
