param([ValidateSet('actor','judge')][string]$Role='actor')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pidName = if ($Role -eq 'actor') { 'model.pid' } else { 'judge.pid' }
$pidFile = Join-Path $projectRoot ('runtime\'+$pidName)
if (-not (Test-Path -LiteralPath $pidFile)) { exit 0 }
$targetPid = [int](Get-Content -LiteralPath $pidFile)
$targetProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$targetPid"
if ($targetProcess) {
    if ($targetProcess.ExecutablePath -ne (Join-Path $projectRoot 'runtime\llama\llama-server.exe')) {
        throw 'Recorded PID no longer belongs to this project model. Refusing to stop it.'
    }
    Stop-Process -Id $targetPid
    Write-Output ('Stopped project '+$Role+' process '+$targetPid)
}
