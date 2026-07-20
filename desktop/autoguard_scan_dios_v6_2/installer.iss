#define MyAppName "AUTOGUARD SCAN DIOS v6.2"
#define MyAppVersion "6.2"
#define MyAppPublisher "Esteban Cortez Richards"
#define MyAppExeName "AUTOGUARD_SCAN_DIOS_v6.2.exe"

[Setup]
AppId={{E2D8233D-7A10-4C4D-BCA0-62B062202026}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName}
AppPublisher={#MyAppPublisher}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Diagnóstico automotriz OBD-II multimarca offline
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={localappdata}\Autoguard\Fusion Scanner DIOS v6.2
DefaultGroupName=AUTOGUARD
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=AUTOGUARD_SCAN_DIOS_v6.2_Setup
SetupIconFile=autoguard.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=classic
WizardSizePercent=100
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
Uninstallable=yes
CreateUninstallRegKey=yes
ChangesAssociations=no
ChangesEnvironment=no
InfoAfterFile=INSTALLATION_NOTES.txt

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
Source: "dist\AUTOGUARD_SCAN_DIOS_v6.2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AUTOGUARD SCAN DIOS v6.2"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\AUTOGUARD SCAN DIOS v6.2"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{autoprograms}\Desinstalar AUTOGUARD SCAN DIOS v6.2"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar AUTOGUARD SCAN DIOS v6.2"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"

[Code]
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpInstalling then
  begin
    WizardForm.StatusLabel.Caption := 'Preparando AUTOGUARD SCAN DIOS v6.2...';
    WizardForm.FilenameLabel.Caption := 'Instalando componentes del programa';
  end;
end;
