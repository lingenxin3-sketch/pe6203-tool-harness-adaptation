$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$executable = Join-Path $projectRoot 'runtime\llama\llama-server.exe'
$modelFile = Join-Path $projectRoot 'runtime\downloads\qwen3-4b-q4.gguf'
if (-not (Test-Path -LiteralPath $executable) -or -not (Test-Path -LiteralPath $modelFile)) {
    throw 'Local runtime/model missing. Run scripts/download_runtime.py and extract llama.zip and cudart.zip first.'
}
try {
    $running = Invoke-RestMethod 'http://127.0.0.1:8081/v1/models' -TimeoutSec 3
    if ($running.data.id -contains 'qwen3-4b') {
        Write-Output 'Project model endpoint is already available on port 8081.'
        exit 0
    }
    throw 'Port 8081 is occupied by a different model.'
} catch [System.Net.Http.HttpRequestException] {
    # No running service: start our project-owned executable below.
}
$arguments = @('-m',('"' + $modelFile + '"'),'--host','127.0.0.1','--port','8081',
    '-ngl','99','-c','16384','--parallel','1','--jinja','--alias','qwen3-4b',
    '--flash-attn','on','--cache-type-k','q8_0','--cache-type-v','q8_0')
$process = Start-Process -FilePath $executable -ArgumentList $arguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $projectRoot 'runtime\model.stdout.log') `
    -RedirectStandardError (Join-Path $projectRoot 'runtime\model.stderr.log')
$process.Id | Set-Content -LiteralPath (Join-Path $projectRoot 'runtime\model.pid')
Write-Output ('Started local model process ' + $process.Id)
