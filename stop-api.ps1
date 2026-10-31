$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\') + '\'
$listeners = @(Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0) { Write-Output 'Local service is not running.'; exit 0 }
$owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
if ($owners.Count -ne 1) { throw 'Unexpected listeners; refusing to stop a process.' }
$servicePid = $owners[0]
$serviceProcess = Get-Process -Id $servicePid
if (-not $serviceProcess.Path -or -not $serviceProcess.Path.StartsWith($projectRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Port 8000 belongs to another program; refusing to stop it.'
}
$health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 5
if ($health.status -ne 'ok') { throw 'Unexpected health response; refusing to stop.' }
$jobs = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/jobs' -TimeoutSec 5
if (@($jobs | Where-Object { $_.status -in @('queued','running') }).Count -gt 0) {
    throw 'A task is still running. Wait for completion before stopping the service.'
}
Stop-Process -Id $servicePid -ErrorAction Stop
Write-Output 'Local AI Paper Agent API stopped.'
