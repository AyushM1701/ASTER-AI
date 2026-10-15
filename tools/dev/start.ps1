param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw 'Run tools/dev/setup.ps1 first to create the local environment.'
}
$runtimeDir = Join-Path $projectRoot 'artifacts\runtime'
New-Item -ItemType Directory -Force -Path $runtimeDir | Out-Null
$api = $null
$ui = $null
$inference = $null
try {
    # Pre-existing listeners are never killed or silently reused.
    foreach ($port in @(8000, 8501)) {
        if (Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue) {
            throw "Port $port is already in use. Stop the existing instance before launching."
        }
    }
    $ollamaExe = Join-Path $projectRoot 'data\models\ollama-runtime\ollama.exe'
    if (Test-Path -LiteralPath $ollamaExe) {
        if (-not (Get-NetTCPConnection -State Listen -LocalPort 11434 -ErrorAction SilentlyContinue)) {
            # Process-local variables: no persistent PATH or system preference changes.
            $env:OLLAMA_HOST = '127.0.0.1:11434'
            $env:OLLAMA_MODELS = Join-Path $projectRoot 'data\models\ollama-store'
            $env:OLLAMA_NO_CLOUD = '1'
            $env:OLLAMA_NUM_PARALLEL = '1'
            $env:OLLAMA_MAX_LOADED_MODELS = '1'
            $inference = Start-Process -FilePath $ollamaExe -ArgumentList @('serve') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir 'ollama.out.log') -RedirectStandardError (Join-Path $runtimeDir 'ollama.err.log')
        }
    }
    $api = Start-Process -FilePath $pythonExe -ArgumentList @('-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000', '--workers', '1', '--no-access-log') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir 'api.out.log') -RedirectStandardError (Join-Path $runtimeDir 'api.err.log')
    $ui = Start-Process -FilePath $pythonExe -ArgumentList @('-m', 'uvicorn', 'frontend.webserver:app', '--host', '127.0.0.1', '--port', '8501', '--workers', '1', '--no-access-log') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir 'ui.out.log') -RedirectStandardError (Join-Path $runtimeDir 'ui.err.log')
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($api.HasExited -or $ui.HasExited) { throw 'A service failed to start. Check artifacts/runtime logs.' }
        try {
            $probe = Invoke-RestMethod 'http://127.0.0.1:8501/_stcore/health' -TimeoutSec 2
            if ($probe -eq 'ok') { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'The UI did not become ready. Check artifacts/runtime logs.' }
    Write-Host 'Aster is running at http://127.0.0.1:8501. Press Ctrl+C to stop both services.'
    if (-not $NoBrowser) { Start-Process 'http://127.0.0.1:8501' }
    while (-not $api.HasExited -and -not $ui.HasExited) { Start-Sleep -Seconds 1 }
} finally {
    if ($null -ne $ui -and -not $ui.HasExited) { Stop-Process -Id $ui.Id -ErrorAction SilentlyContinue }
    if ($null -ne $api -and -not $api.HasExited) { Stop-Process -Id $api.Id -ErrorAction SilentlyContinue }
    if ($null -ne $inference -and -not $inference.HasExited) { Stop-Process -Id $inference.Id -ErrorAction SilentlyContinue }
}
