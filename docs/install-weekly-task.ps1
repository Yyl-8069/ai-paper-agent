$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$taskName = 'AI Paper Agent Weekly'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$xmlAction = [Security.SecurityElement]::Escape("-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File " + '"' + "$projectRoot/docs/run-weekly.ps1" + '"')
$xmlRoot = [Security.SecurityElement]::Escape($projectRoot)
$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Weekly summaries of manually collected papers; no collection or deletion.</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>2026-11-01T21:00:00+08:00</StartBoundary><Enabled>true</Enabled><ScheduleByWeek><WeeksInterval>1</WeeksInterval><DaysOfWeek><Sunday /></DaysOfWeek></ScheduleByWeek></CalendarTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>$identity</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><AllowHardTerminate>true</AllowHardTerminate><StartWhenAvailable>true</StartWhenAvailable><RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable><Enabled>true</Enabled><Hidden>true</Hidden><ExecutionTimeLimit>PT30M</ExecutionTimeLimit></Settings>
  <Actions Context="Author"><Exec><Command>powershell.exe</Command><Arguments>$xmlAction</Arguments><WorkingDirectory>$xmlRoot</WorkingDirectory></Exec></Actions>
</Task>
"@
$taskPath = Join-Path $PSScriptRoot 'weekly-task.xml'
[IO.File]::WriteAllText($taskPath, $taskXml, [Text.Encoding]::Unicode)
& schtasks.exe /Query /TN $taskName *> $null
if ($LASTEXITCODE -eq 0) { throw "Task already exists. Inspect it in Windows Task Scheduler before replacing." }
& schtasks.exe /Create /TN $taskName /XML $taskPath
if ($LASTEXITCODE -ne 0) { throw "Task creation failed." }
& schtasks.exe /Query /TN $taskName /FO LIST
