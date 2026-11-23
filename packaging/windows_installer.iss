#ifndef MyAppVersion
  #define MyAppVersion "0.2.0"
#endif

[Setup]
AppId={{E6B2D24A-9A67-4B8F-9E29-31D4E40C8A1F}
AppName=PradoOS
AppVersion={#MyAppVersion}
AppPublisher=PradoOS (Universidad de Granada - Open Source)
AppPublisherURL=https://github.com/LorSt4r/prado-os
AppSupportURL=https://github.com/LorSt4r/prado-os/issues
DefaultDirName={localappdata}\PradoOS
DefaultGroupName=PradoOS
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
AppMutex=Local\PradoOS_Desktop_SingleInstance
CloseApplications=force
RestartApplications=no
OutputDir=..\dist
OutputBaseFilename=PradoOS-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\PradoOS.exe
Compression=lzma2/normal
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\PradoOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PradoOS"; Filename: "{app}\PradoOS.exe"
Name: "{group}\{cm:UninstallProgram,PradoOS}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PradoOS"; Filename: "{app}\PradoOS.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PradoOS.exe"; Description: "{cm:LaunchProgram,PradoOS}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\PradoOS.exe"; Flags: nowait skipifnotsilent

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/IM PradoOS.exe /T /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;
