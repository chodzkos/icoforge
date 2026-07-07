; Inno Setup script for IcoForge
; Build with: iscc /DAppVersion=0.1.0 installer\icoforge.iss
; (AppVersion is injected by the build script / CI)

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName      "IcoForge"
#define AppPublisher "Marcin"
#define AppURL       "https://github.com/chodzkos/icoforge"
#define AppExeName   "IcoForge.exe"

[Setup]
AppId={{A3F2C1D0-7B4E-4F8A-9C2D-1E5B6A3F0D7C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Offer user/machine install choice at UAC prompt
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename={#AppName}-{#AppVersion}-setup
SetupIconFile=..\assets\icoforge.ico
WizardSmallImageFile=compiler:WizClassicSmallImage.bmp
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Minimum Windows 10
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "polish";  MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
  Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; \
  Flags: unchecked

[Files]
Source: "..\dist\{#AppName}\*"; \
  DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs
; Third-party license notices (LGPL/BSD/MIT). Also bundled by the PyInstaller
; spec; installed explicitly so the notices ship even for a hand-built dist.
Source: "..\THIRD_PARTY_LICENSES.txt"; \
  DestDir: "{app}"; \
  Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  IconFilename: "{app}\icoforge.ico"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
; Desktop (optional task)
Name: "{autodesktop}\{#AppName}"; \
  Filename: "{app}\{#AppExeName}"; \
  IconFilename: "{app}\icoforge.ico"; \
  Tasks: desktopicon

[Registry]
; Optional .ico file association
Root: HKCR; Subkey: ".ico\OpenWithProgids"; \
  ValueType: string; ValueName: "IcoForge.AssocFile.ICO"; ValueData: ""; \
  Flags: uninsdeletevalue
Root: HKCR; Subkey: "IcoForge.AssocFile.ICO"; \
  ValueType: string; ValueName: ""; ValueData: "ICO Icon File"; \
  Flags: uninsdeletekey
Root: HKCR; Subkey: "IcoForge.AssocFile.ICO\DefaultIcon"; \
  ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExeName},0"
Root: HKCR; Subkey: "IcoForge.AssocFile.ICO\shell\open"; \
  ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"
Root: HKCR; Subkey: "IcoForge.AssocFile.ICO\shell\open\command"; \
  ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExeName}"" ""%1"""

[Run]
Filename: "{app}\{#AppExeName}"; \
  Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent
