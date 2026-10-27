$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$executable = Join-Path $projectRoot 'runtime\llama\llama-server.exe'
$modelFile = Join-Path $projectRoot 'runtime\downloads\qwen2.5-7b-instruct-q4_k_m-00001-of-00002.gguf'
$capacity = (Get-Content -LiteralPath (Join-Path $projectRoot 'configs\judge-capacity.json') -Raw | ConvertFrom-Json).context_tokens
if (-not (Test-Path -LiteralPath $modelFile)) { throw 'Run scripts/download_runtime.py --judge-only first.' }
try {
    $running = Invoke-RestMethod 'http://127.0.0.1:8082/v1/models' -TimeoutSec 3
    if ($running.data.id -contains 'qwen2.5-7b-judge') {
        $properties = Invoke-RestMethod 'http://127.0.0.1:8082/props' -TimeoutSec 3
        if ($properties.default_generation_settings.n_ctx -ne $capacity) {
            throw 'Existing judge has a different context capacity; inspect and stop the owned judge before restarting.'
        }
        Write-Output 'Project judge is already running.'
        exit 0
    }
    throw 'Port 8082 is occupied by a different model.'
} catch [System.Net.Http.HttpRequestException] {
}
$arguments = @('-m',('"' + $modelFile + '"'),'--host','127.0.0.1','--port','8082',
    '-ngl','20','-c',([string]$capacity),'--parallel','1','--jinja','--alias','qwen2.5-7b-judge',
    '--flash-attn','on','--cache-type-k','q8_0','--cache-type-v','q8_0','-t','8')
$process = Start-Process -FilePath $executable -ArgumentList $arguments -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $projectRoot 'runtime\judge.stdout.log') `
    -RedirectStandardError (Join-Path $projectRoot 'runtime\judge.stderr.log')
$process.Id | Set-Content -LiteralPath (Join-Path $projectRoot 'runtime\judge.pid')
Write-Output ('Started judge process ' + $process.Id)
