#define PatchName "AUTOGUARD SCAN DIOS v6.2.6 - PARCHE CONSOLIDADO"
#define PatchVersion "6.2.6.2026.07.20"
#define Publisher "Esteban Cortez Richards"
#define AppExeName "AUTOGUARD_SCAN_DIOS_v6.2.exe"
#define OutputName "AUTOGUARD_SCAN_DIOS_v6.2.6_PARCHE_CONSOLIDADO_Setup"

[Setup]
AppId={{C15A2D7B-7E6F-4E1D-9D72-20260720A626}
AppName={#PatchName}
AppVersion={#PatchVersion}
AppVerName={#PatchName}
AppPublisher={#Publisher}
VersionInfoCompany={#Publisher}
VersionInfoDescription=Parche consolidado con inicio en menú, navegación fluida, informe maestro y recuperación automática
VersionInfoProductName={#PatchName}
VersionInfoProductVersion={#PatchVersion}
DefaultDirName={code:GetInstallDir}
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=patch_output
OutputBaseFilename={#OutputName}
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

[Files]
Source: "dist\AUTOGUARD_SCAN_DIOS_v6.2\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir AUTOGUARD SCAN DIOS actualizado"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent; Check: IsPatchCommitted

[Code]
const
  InstalledAppId = '{E2D8233D-7A10-4C4D-BCA0-62B062202026}_is1';
  RollbackExitCode = 20;

var
  CachedInstallDir: string;
  BackupDir: string;
  BackupPayloadDir: string;
  BackupCreated: Boolean;
  PatchPrepared: Boolean;
  PatchCommitted: Boolean;
  PatchFailed: Boolean;
  RollbackCompleted: Boolean;
  FailureReason: string;

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
    Candidate := RemoveBackslashUnlessRoot(Candidate);

  if Candidate = '' then
    Candidate := ExpandConstant('{localappdata}\Autoguard\Fusion Scanner DIOS v6.2');

  CachedInstallDir := RemoveBackslashUnlessRoot(Candidate);
  Result := CachedInstallDir;
end;

function GetInstallDir(Param: string): string;
begin
  Result := ResolveInstallDir;
end;

function IsPatchCommitted: Boolean;
begin
  Result := PatchCommitted and (not PatchFailed);
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

function RobocopySucceeded(ResultCode: Integer): Boolean;
begin
  Result := (ResultCode >= 0) and (ResultCode < 8);
end;

function CreateInstallationBackup: Boolean;
var
  ResultCode: Integer;
  BackupRoot: string;
  Parameters: string;
  ManifestText: string;
  SourceDir: string;
begin
  Result := False;
  if BackupCreated then
  begin
    Result := True;
    exit;
  end;

  SourceDir := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  if not FileExists(AddBackslash(SourceDir) + '{#AppExeName}') then
  begin
    FailureReason := 'No se encontró una instalación válida de AUTOGUARD SCAN DIOS en: ' + SourceDir;
    exit;
  end;

  BackupRoot := ExpandConstant('{localappdata}\Autoguard\Backups');
  ForceDirectories(BackupRoot);
  BackupDir := AddBackslash(BackupRoot) + 'Consolidado_v6.2.6_' + GetDateTimeString('yyyymmdd_hhnnss', '', '');
  BackupPayloadDir := AddBackslash(BackupDir) + 'Instalacion_anterior';
  ForceDirectories(BackupPayloadDir);

  Parameters := '"' + SourceDir + '" "' + BackupPayloadDir + '" /E /COPY:DAT /DCOPY:T /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /XD logs';
  ResultCode := 16;
  if not Exec(
    ExpandConstant('{sys}\robocopy.exe'),
    Parameters,
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) then
  begin
    FailureReason := 'Windows no pudo ejecutar la copia de respaldo.';
    exit;
  end;

  if not RobocopySucceeded(ResultCode) then
  begin
    FailureReason := 'El respaldo previo terminó con código robocopy ' + IntToStr(ResultCode) + '.';
    exit;
  end;

  ManifestText :=
    'RESPALDO AUTOMÁTICO AUTOGUARD SCAN DIOS' + #13#10 +
    'Fecha: ' + GetDateTimeString('dd/mm/yyyy hh:nn:ss', '', '') + #13#10 +
    'Origen: ' + SourceDir + #13#10 +
    'Contenido: ' + BackupPayloadDir + #13#10 +
    'Resultado robocopy: ' + IntToStr(ResultCode) + #13#10 +
    'Parche: v6.2.6 consolidado' + #13#10;
  SaveStringToFile(AddBackslash(BackupDir) + 'RESPALDO_AUTOGUARD.txt', ManifestText, False);

  BackupCreated := True;
  Result := True;
end;

function RestorePreviousInstallation: Boolean;
var
  AppDir: string;
  Parameters: string;
  ResultCode: Integer;
begin
  Result := False;
  if RollbackCompleted then
  begin
    Result := True;
    exit;
  end;
  if (not BackupCreated) or (not DirExists(BackupPayloadDir)) then
    exit;

  StopAutoguard;
  AppDir := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  DelTree(AppDir, True, True, True);
  ForceDirectories(AppDir);

  Parameters := '"' + BackupPayloadDir + '" "' + AppDir + '" /MIR /COPY:DAT /DCOPY:T /R:1 /W:1 /NFL /NDL /NJH /NJS /NP';
  ResultCode := 16;
  if Exec(
    ExpandConstant('{sys}\robocopy.exe'),
    Parameters,
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) and RobocopySucceeded(ResultCode) then
  begin
    RollbackCompleted := True;
    SaveStringToFile(
      AddBackslash(BackupDir) + 'RESTAURACION_AUTOMATICA.txt',
      'La instalación anterior fue restaurada automáticamente el ' +
      GetDateTimeString('dd/mm/yyyy hh:nn:ss', '', '') + #13#10 +
      'Motivo: ' + FailureReason + #13#10,
      False
    );
    Result := True;
  end;
end;

procedure PreparePatch;
var
  AppDir: string;
begin
  if PatchPrepared then
    exit;

  StopAutoguard;
  if not CreateInstallationBackup then
  begin
    PatchFailed := True;
    if FailureReason = '' then
      FailureReason := 'No fue posible crear el respaldo previo.';
    SuppressibleMsgBox(
      FailureReason + #13#10 + #13#10 + 'No se modificó la instalación existente.',
      mbError,
      MB_OK,
      IDOK
    );
    Abort;
  end;

  AppDir := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  DeleteFile(AddBackslash(AppDir) + '{#AppExeName}');
  DelTree(AddBackslash(AppDir) + '_internal', True, True, True);
  PatchPrepared := True;
end;

function ValidateInstalledPayload: Boolean;
var
  AppDir: string;
begin
  AppDir := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  Result :=
    FileExists(AddBackslash(AppDir) + '{#AppExeName}') and
    FileExists(AddBackslash(AppDir) + '_internal\data\autoguard_dtc.sqlite');
  if not Result then
    FailureReason := 'El parche no dejó instalados el ejecutable y la base DTC requeridos.';
end;

function RunApplicationSelfTest: Boolean;
var
  AppDir: string;
  ExePath: string;
  ResultCode: Integer;
begin
  Result := False;
  AppDir := RemoveBackslashUnlessRoot(ExpandConstant('{app}'));
  ExePath := AddBackslash(AppDir) + '{#AppExeName}';
  ResultCode := -1;

  if not Exec(
    ExePath,
    '--autoguard-self-test',
    AppDir,
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) then
  begin
    FailureReason := 'Windows no pudo ejecutar la autoprueba de AUTOGUARD.';
    exit;
  end;

  if ResultCode <> 0 then
  begin
    FailureReason := 'La autoprueba gráfica terminó con código ' + IntToStr(ResultCode) + '.';
    exit;
  end;

  Result := True;
end;

procedure FailAndRollback(const Reason: string);
var
  Restored: Boolean;
begin
  PatchFailed := True;
  FailureReason := Reason;
  Restored := RestorePreviousInstallation;
  if Restored then
    FailureReason := FailureReason + #13#10 + #13#10 + 'La versión anterior fue restaurada automáticamente.'
  else
    FailureReason := FailureReason + #13#10 + #13#10 + 'No fue posible completar la restauración automática. El respaldo permanece en: ' + BackupDir;

  SuppressibleMsgBox(FailureReason, mbError, MB_OK, IDOK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    PreparePatch;
  end
  else if CurStep = ssPostInstall then
  begin
    if not ValidateInstalledPayload then
      FailAndRollback(FailureReason)
    else if not RunApplicationSelfTest then
      FailAndRollback(FailureReason)
    else
    begin
      PatchCommitted := True;
      SaveStringToFile(
        AddBackslash(BackupDir) + 'PARCHE_APLICADO_CORRECTAMENTE.txt',
        'AUTOGUARD SCAN DIOS v6.2.6 fue validado y quedó activo el ' +
        GetDateTimeString('dd/mm/yyyy hh:nn:ss', '', '') + #13#10,
        False
      );
    end;
  end;
end;

procedure DeinitializeSetup;
begin
  if BackupCreated and (not PatchCommitted) and (not RollbackCompleted) then
  begin
    if FailureReason = '' then
      FailureReason := 'La instalación no terminó correctamente o fue cancelada.';
    RestorePreviousInstallation;
  end;
end;

function GetCustomSetupExitCode: Integer;
begin
  if PatchFailed then
    Result := RollbackExitCode
  else
    Result := 0;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpInstalling then
  begin
    WizardForm.StatusLabel.Caption := 'Aplicando parche consolidado AUTOGUARD...';
    WizardForm.FilenameLabel.Caption := 'Respaldando, optimizando navegación y validando la aplicación';
  end
  else if (CurPageID = wpFinished) and PatchCommitted then
  begin
    WizardForm.FinishedLabel.Caption :=
      'La actualización fue instalada y validada correctamente.' + #13#10 +
      'AUTOGUARD iniciará directamente en el menú principal.';
  end;
end;
