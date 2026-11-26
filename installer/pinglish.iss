; Inno Setup script for the Pinglish Windows installer.
; Build from the project root:  .\installer\build.ps1
; (needs dist\Pinglish from PyInstaller first; build.ps1 does both)

#ifndef AppVersion
  #define AppVersion "1.02"
#endif
#define AppName "Pinglish"
#define AppExe "Pinglish.exe"
#define AppUrl "https://github.com/MindDriverTUWIEN/Pinglish"
; Same ID the app gives its window, so a pinned shortcut and the window share one taskbar icon.
#define AppUserModelID "Local.Finglish.Desktop"

[Setup]
AppId={{6F1C2A4E-5B7D-4C3A-9E2F-8D1B0A7C6E54}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=MindDriverTUWIEN
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}/issues
AppUpdatesURL={#AppUrl}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
; Shown before the options page: what is sent to Google, and how to turn it off.
InfoBeforeFile=privacy.txt
; Installs for the current user without admin rights; users may choose all users.
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist
OutputBaseFilename=Pinglish-Setup-{#AppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "speech"; Description: "Enable speech recognition (the mic sends your speech to Google, see the privacy page)"; GroupDescription: "Speech recognition:"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "autostart"; Description: "Start Pinglish when I sign in to Windows (runs in the tray)"; GroupDescription: "Other options:"; Flags: unchecked

[Files]
Source: "..\dist\Pinglish\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[INI]
; Read by paths.speech_enabled(); enabled=0 keeps the mic from recording or sending anything.
Filename: "{app}\pinglish.ini"; Section: "speech"; Key: "enabled"; String: "1"; Tasks: speech; Flags: uninsdeletesection
Filename: "{app}\pinglish.ini"; Section: "speech"; Key: "enabled"; String: "0"; Tasks: not speech; Flags: uninsdeletesection

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "{#AppUserModelID}"; Tasks: desktopicon
Name: "{userstartup}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\pinglish.ini"

[UninstallRun]
; Quit a running Pinglish (and its window) before files are removed.
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM {#AppExe}"; Flags: runhidden; RunOnceId: "StopPinglish"

; User data in %LOCALAPPDATA%\Pinglish (corrections, settings) is kept on uninstall.
