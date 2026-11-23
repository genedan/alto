; Inno Setup script for the Windows installer of Alto: iscc /DAppVersion=0.0.0 packaging\windows\alto.iss
; scripts\build-windows.ps1 runs it, after PyInstaller has made dist\alto.
;
; The installer is for one user: no administrator prompt, Alto in %LOCALAPPDATA%\Programs\Alto, an entry in the Start menu and in
; Settings > Apps. Running a newer installer over an older one updates it, because AppId stays the same. The uninstaller asks
; whether to also remove the practice history and the settings, and a silent uninstall keeps them unless /PURGE=1 is given.

#ifndef AppVersion
  #error Pass the version: iscc /DAppVersion=0.0.0 packaging\windows\alto.iss
#endif
; SourceDir: the folder PyInstaller made. OutputDir: where the installer is written. IconFile: an .ico, if there is one.
#ifndef SourceDir
  #define SourceDir "..\..\dist\alto"
#endif
#ifndef OutputDir
  #define OutputDir "..\..\dist"
#endif

[Setup]
; Never change this: it is how a newer installer finds the copy it should update.
AppId={{26F851E3-0F09-45A0-A9C4-13D12F91DA07}
AppName=Alto
AppVersion={#AppVersion}
AppPublisher=Alto
AppPublisherURL=https://github.com/altosaurus/alto
AppSupportURL=https://github.com/altosaurus/alto/issues
AppUpdatesURL=https://github.com/altosaurus/alto/releases
DefaultDirName={autopf}\Alto
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\..\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename=alto-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; An update started from inside Alto closes it with /CLOSEAPPLICATIONS and starts it again with /RELAUNCH=1 (see [Run] below), so the
; installer's own restart of the programs it closed is off: Alto would be started twice.
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\alto.exe
#ifdef IconFile
SetupIconFile={#IconFile}
#endif

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; Flags: unchecked

[InstallDelete]
; Version 0.0.2 bundled these optional Qt components. In-place updates leave obsolete files behind.
Type: files; Name: "{app}\_internal\PySide6\plugins\platforminputcontexts\qtvirtualkeyboardplugin.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6VirtualKeyboard.dll"
Type: files; Name: "{app}\_internal\PySide6\plugins\multimedia\ffmpegmediaplugin.dll"
Type: files; Name: "{app}\_internal\PySide6\avcodec-63.dll"
Type: files; Name: "{app}\_internal\PySide6\avformat-63.dll"
Type: files; Name: "{app}\_internal\PySide6\avutil-61.dll"
Type: files; Name: "{app}\_internal\PySide6\swresample-7.dll"
Type: files; Name: "{app}\_internal\PySide6\swscale-10.dll"

Type: files; Name: "{app}\_internal\PySide6\plugins\imageformats\qpdf.dll"
Type: files; Name: "{app}\_internal\PySide6\Qt6Pdf.dll"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Alto"; Filename: "{app}\alto.exe"
Name: "{autodesktop}\Alto"; Filename: "{app}\alto.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\alto.exe"; Description: "Start Alto"; Flags: nowait postinstall skipifsilent
; After an update that Alto started itself, which is silent and given /RELAUNCH=1: open Alto again.
Filename: "{app}\alto.exe"; Flags: nowait; Check: ShouldRelaunch

[Code]
function ShouldRelaunch: Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

{ Alto keeps its practice history in %APPDATA%\Alto and its settings in the registry under HKEY_CURRENT_USER\Software\alto. }
procedure RemoveUserData;
begin
  DelTree(ExpandConstant('{userappdata}\Alto'), True, True, True);
  RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\alto');
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep <> usPostUninstall then
    Exit;
  if UninstallSilent then
  begin
    { A silent uninstall never asks, and keeps the data unless it was told to remove it: Unins000.exe /VERYSILENT /PURGE=1 }
    if ExpandConstant('{param:PURGE|0}') = '1' then
      RemoveUserData;
  end
  else if MsgBox('Alto has been removed.' + #13#10 + #13#10 +
                 'Also remove your practice history and your settings? Choose No to keep them, for example to install Alto again later.',
                 mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
    RemoveUserData;
end;
