#define MyAppName "SuperScan 2.0 Profesional"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "AutoGuard Servicios"
#define MyAppExeName "SuperScan 2.0.exe"

[Setup]
AppId={{A8B97358-457E-4C75-A745-2C1316CD9133}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Diagnóstico automotriz profesional multimarca OBD-II
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
DefaultDirName={localappdata}\SuperScan\2.0 Profesional
DefaultGroupName=SuperScan 2.0 Profesional
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=SuperScan 2.0 Profesional Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
UninstallDisplayName={#MyAppName}
CreateUninstallRegKey=yes
SetupLogging=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\SuperScan 2.0\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\SuperScan 2.0 Profesional"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\SuperScan 2.0 Profesional"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Iniciar SuperScan 2.0 Profesional"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure InitializeWizard;
begin
  WizardForm.WelcomeLabel2.Caption :=
    'Instala SuperScan 2.0 Profesional con interfaz AutoGuard, conexión COM/Wi-Fi/simulador, 12.133 DTC, soluciones offline, datos en vivo, gráficos HD e informes PDF con planes de acción.';
end;
