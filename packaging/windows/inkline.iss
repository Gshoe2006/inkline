; Inkline's Windows installer (Inno Setup 6). packaging/windows/build.py runs it with /DVERSION, /DAPPDIR (the app
; folder PyInstaller built), /DOUTDIR, /DICON and /DLICENSE.

#ifndef VERSION
  #error Run this through packaging/windows/build.py
#endif

[Setup]
AppId={{6F1B7F0A-3C2E-4E9B-9C55-1D2B7A4E8C31}
AppName=Inkline
AppVersion={#VERSION}
AppVerName=Inkline {#VERSION}
AppPublisher=Inkline
AppPublisherURL=https://github.com/Gshoe2006/inkline
AppSupportURL=https://github.com/Gshoe2006/inkline/issues
; the installer's own file details: SignPath only signs a file whose product name and version are these
VersionInfoProductName=Inkline
VersionInfoProductVersion={#VERSION}
VersionInfoProductTextVersion={#VERSION}
VersionInfoVersion={#VERSION}
VersionInfoDescription=Inkline installer
DefaultDirName={autopf}\Inkline
DefaultGroupName=Inkline
DisableProgramGroupPage=yes
; installs for the current user without asking for an administrator; "Install for all users" is offered too
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
LicenseFile={#LICENSE}
OutputDir={#OUTDIR}
OutputBaseFilename=inkline-{#VERSION}-windows-setup
SetupIconFile={#ICON}
UninstallDisplayIcon={app}\Inkline.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#APPDIR}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Inkline"; Filename: "{app}\Inkline.exe"; AppUserModelID: "Gshoe2006.Inkline"
Name: "{autodesktop}\Inkline"; Filename: "{app}\Inkline.exe"; Tasks: desktopicon; AppUserModelID: "Gshoe2006.Inkline"

[Registry]
; .inkline projects open in Inkline with a double-click, with Inkline's icon
Root: HKA; Subkey: "Software\Classes\.inkline"; ValueType: string; ValueName: ""; ValueData: "Inkline.Project"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Inkline.Project"; ValueType: string; ValueName: ""; ValueData: "Inkline project"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Inkline.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Inkline.exe,0"
Root: HKA; Subkey: "Software\Classes\Inkline.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Inkline.exe"" ""%1"""

[UninstallRun]
; the update check Help -> Check for updates automatically set up, if any (none there is fine)
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""Inkline update check"" /F"; Flags: runhidden; RunOnceId: "DelUpdateTask"
Filename: "{sys}\reg.exe"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v ""Inkline update check"" /f"; Flags: runhidden; RunOnceId: "DelUpdateLogin"

[Run]
Filename: "{app}\Inkline.exe"; Description: "{cm:LaunchProgram,Inkline}"; Flags: nowait postinstall skipifsilent
