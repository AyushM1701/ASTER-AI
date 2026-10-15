# Explicit network setup for the shared text/vision model. Never run by an API request.
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$runtimeRoot = Join-Path $projectRoot 'data\models\ollama-runtime'
$runtimeArchive = Join-Path $runtimeRoot 'runtime.zip'
$ollamaExe = Join-Path $runtimeRoot 'ollama.exe'
$expectedHash = 'dc50b9ca7f9023c86525012632cd1615b093d0407987444a7f62ecab617e8e93'
New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
if (-not (Test-Path -LiteralPath $ollamaExe)) {
    if (-not (Test-Path -LiteralPath $runtimeArchive)) {
        Invoke-WebRequest 'https://github.com/ollama/ollama/releases/download/v0.35.1/ollama-windows-amd64.zip' -OutFile $runtimeArchive
    }
    if ((Get-FileHash -LiteralPath $runtimeArchive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expectedHash) {
        throw 'Runtime archive checksum mismatch. No downloaded executable was run.'
    }
    Expand-Archive -LiteralPath $runtimeArchive -DestinationPath $runtimeRoot -Force
}
$env:OLLAMA_HOST = '127.0.0.1:11434'
$env:OLLAMA_MODELS = Join-Path $projectRoot 'data\models\ollama-store'
$env:OLLAMA_NO_CLOUD = '1'
$env:OLLAMA_NUM_PARALLEL = '1'
$env:OLLAMA_MAX_LOADED_MODELS = '1'
$inference = $null
try {
    if (-not (Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction SilentlyContinue)) {
        $inference = Start-Process -FilePath $ollamaExe -ArgumentList @('serve') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
        $available = $false
        for ($attempt = 0; $attempt -lt 30; $attempt++) {
            try {
                $null = Invoke-RestMethod 'http://127.0.0.1:11434/api/version' -TimeoutSec 2
                $available = $true
                break
            } catch { Start-Sleep -Seconds 1 }
        }
        if (-not $available) { throw 'Local Ollama did not start.' }
    }
    & $ollamaExe pull 'qwen3-vl:2b-instruct'
    if ($LASTEXITCODE -ne 0) { throw 'Model pull failed; rerun to resume.' }
    Write-Host 'Shared text/vision model downloaded. Configure .env as described in README.md and run tools/dev/start.ps1.'
} finally {
    if ($null -ne $inference -and -not $inference.HasExited) { Stop-Process -Id $inference.Id -ErrorAction SilentlyContinue }
}
