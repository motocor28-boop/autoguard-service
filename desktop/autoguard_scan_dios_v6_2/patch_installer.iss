#define PatchName "AUTOGUARD SCAN DIOS v6.2.2 - PARCHE INFORME MAESTRO"
#define PatchVersion "6.2.2.2026.07.20"
#define Publisher "Esteban Cortez Richards"
#define AppExeName "AUTOGUARD_SCAN_DIOS_v6.2.exe"

[Setup]
AppId={{C15A2D7B-7E6F-4E1D-9D72-20260720A622}
AppName={#PatchName}
AppVersion={#PatchVersion}
AppVerName={#PatchName}
AppPublisher={#Publisher}
VersionInfoCompany={#Publisher}
VersionInfoDescription=Parche de informe técnico maestro con gráficos HD y procedimientos de reparación
VersionInfoProductName={#PatchName}
VersionInfoProductVersion={#PatchVersion}
DefaultDirName={code:GetInstallDir}
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=patch_output
OutputBaseFilename=AUTOGUARD_SCAN_DIOS_v6.2.2_PATCH_INFORME_MAESTRO_Setup
SetupIconFile=autoguard.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=classic
WizardSizePercent=110
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
Uninstallable=no
CreateUninstallRegKey=no
ChangesAssociations=no
ChangesEnvironment=no
InfoAfterFile=PATCH_NOTES_INFORME_MAESTRO.txt

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[InstallDelete]
Type: files; Name: "{app}\{#AppExeName}"
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\AUTOGUARD_SCAN_DIOS_v6.2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir AUTOGUARD SCAN DIOS actualizado"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[Code]
const
  InstalledAppId = '{E2D8233D-7A10-4C4D-BCA0-62B062202026}_is1';

var
  CachedInstallDir: string;
  BackupDir: string;

function ResolveInstallDir: string;
var
  RegistryPath: string;
  Candidate: string;
begin
  if CachedInstallDir <> '' then
  begin
    Result := CachedInstallDir;
    exit;
  end;

  RegistryPath := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + InstalledAppId;
  Candidate := '';

  if RegQueryStringValue(HKCU, RegistryPath, 'InstallLocation', Candidate) then
  begin
    Candidate := RemoveBackslashUnlessRoot(Candidate);
  end;

  if Candidate = '' then
  begin
    Candidate := ExpandConstant('{localappdata}\Autoguard\Fusion Scanner DIOS v6.2');
  end;

  CachedInstallDir := RemoveBackslashUnlessRoot(Candidate);
  Result := CachedInstallDir;
end;

function GetInstallDir(Param: string): string;
begin
  Result := ResolveInstallDir;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  AppPath: string;
begin
  AppPath := AddBackslash(ExpandConstant('{app}')) + '{#AppExeName}';
  if not FileExists(AppPath) then
  begin
    Result :=
      'No se encontró una instalación válida de AUTOGUARD SCAN DIOS v6.2.2 en:' + #13#10 +
      ExpandConstant('{app}') + #13#10 + #13#10 +
      'Instale primero la versión completa y luego ejecute este parche.';
    exit;
  end;
  Result := '';
end;

procedure StopAutoguard;
var
  ResultCode: Integer;
begin
  Exec(
    ExpandConstant('{sys}\taskkill.exe'),
    '/F /IM "{#AppExeName}"',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  );
  Sleep(700);
end;

procedure CreateInstallationBackup;
var
  ResultCode: Integer;
  BackupRoot: string;
  Parameters: string;
  ManifestText: string;
  SourceDir: string;
begin
  SourceDir := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  BackupRoot := ExpandConstant('{localappdata}\Autoguard\Backups');
  ForceDirectories(BackupRoot);
  BackupDir := AddBackslash(BackupRoot) + 'Informe_Premium_' + GetDateTimeString('yyyymmdd_hhnnss', '', '');
  ForceDirectories(BackupDir);

  Parameters := '"' + SourceDir + '" "' + BackupDir + '" /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /XD logs';
  Exec(
    ExpandConstant('{sys}\robocopy.exe'),
    Parameters,
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  );

  ManifestText :=
    'RESPALDO AUTOMÁTICO AUTOGUARD SCAN DIOS' + #13#10 +
    'Fecha: ' + GetDateTimeString('dd/mm/yyyy hh:nn:ss', '', '') + #13#10 +
    'Origen: ' + SourceDir + #13#10 +
    'Resultado robocopy: ' + IntToStr(ResultCode) + #13#10 +
    'Parche: Informe Maestro Premium' + #13#10;
  SaveStringToFile(AddBackslash(BackupDir) + 'RESPALDO_AUTOGUARD.txt', ManifestText, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    StopAutoguard;
    CreateInstallationBackup;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpInstalling then
  begin
    WizardForm.StatusLabel.Caption := 'Aplicando parche de Informe Maestro Premium...';
    WizardForm.FilenameLabel.Caption := 'Respaldando instalación y actualizando gráficos HD, descripciones y procedimientos';
  end;
end;
