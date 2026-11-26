; Inno Setup script for the Pinglish Windows installer.
; Build from the project root:  .\installer\build.ps1
; (needs dist\Pinglish from PyInstaller first; build.ps1 does both)

#ifndef AppVersion
  #define AppVersion "1.03"
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

[Code]
// Tell the user when Pinglish is already installed, instead of silently
// installing again. Inno Setup stores the installed version under the AppId.
const
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{6F1C2A4E-5B7D-4C3A-9E2F-8D1B0A7C6E54}_is1';

function GetInstalledVersion(var Version: String): Boolean;
begin
  // Per-user install (the default) first, then an install for all users.
  Result := RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', Version);
  if not Result then
    Result := RegQueryStringValue(HKLM64, UninstallKey, 'DisplayVersion', Version);
  if not Result then
    Result := RegQueryStringValue(HKLM32, UninstallKey, 'DisplayVersion', Version);
end;

// Takes the next number off a dotted version: "1.03" gives 1, then 3.
function NextVersionPart(var S: String): Integer;
var
  P: Integer;
begin
  P := Pos('.', S);
  if P = 0 then
  begin
    Result := StrToIntDef(Trim(S), 0);
    S := '';
  end
  else
  begin
    Result := StrToIntDef(Trim(Copy(S, 1, P - 1)), 0);
    Delete(S, 1, P);
  end;
end;

// 1 when A is newer than B, -1 when older, 0 when the same.
function CompareVersions(A, B: String): Integer;
var
  X, Y: Integer;
begin
  Result := 0;
  while (Result = 0) and ((A <> '') or (B <> '')) do
  begin
    X := NextVersionPart(A);
    Y := NextVersionPart(B);
    if X > Y then
      Result := 1
    else if X < Y then
      Result := -1;
  end;
end;

function InitializeSetup(): Boolean;
var
  Installed: String;
  Cmp: Integer;
begin
  Result := True;
  if not GetInstalledVersion(Installed) then
    Exit;

  Cmp := CompareVersions(Installed, '{#AppVersion}');
  if Cmp = 0 then
    Result := SuppressibleMsgBox(
      '{#AppName} {#AppVersion} is already installed on this computer.' + #13#10#13#10 +
      'Do you want to install it again? This repairs the installation.' + #13#10 +
      'Your settings and word corrections are kept.',
      mbConfirmation, MB_YESNO, IDYES) = IDYES
  else if Cmp > 0 then
    Result := SuppressibleMsgBox(
      'A newer version of {#AppName} (' + Installed + ') is already installed.' + #13#10#13#10 +
      'Do you want to replace it with the older version {#AppVersion}?',
      mbConfirmation, MB_YESNO or MB_DEFBUTTON2, IDNO) = IDYES
  else
    Result := SuppressibleMsgBox(
      '{#AppName} ' + Installed + ' is installed on this computer.' + #13#10#13#10 +
      'Setup will update it to version {#AppVersion}.' + #13#10 +
      'Your settings and word corrections are kept.',
      mbInformation, MB_OKCANCEL, IDOK) = IDOK;
end;
