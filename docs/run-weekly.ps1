$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:TEMP = Join-Path $projectRoot 'tmp'
$env:TMP = $env:TEMP
$env:PYTHONUTF8 = '1'
$logRoot = Join-Path $projectRoot 'library/logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
New-Item -ItemType Directory -Path $env:TEMP -Force | Out-Null
$logFile = Join-Path $logRoot ("weekly-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.log')
& "$projectRoot/.venv/Scripts/python.exe" -X utf8 -m app.cli catch-up *> $logFile
exit $LASTEXITCODE
