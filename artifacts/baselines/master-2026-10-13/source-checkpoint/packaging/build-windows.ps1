param(
    [ValidateSet('ValidationOnly','PublicStandard','PrivateAuthorized')][string]$Edition = 'ValidationOnly',
    [string]$Version = '0.1.0-beta.1',
    [string]$Python = '',
    [switch]$SkipTests
)
$ErrorActionPreference = 'Stop'
if ($Version -notmatch '^[0-9][A-Za-z0-9_.-]{0,60}$') { throw 'Use a canonical version, for example 0.1.0-beta.1.' }
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
if (-not $Python) { $Python = Join-Path $projectRoot '.venv/Scripts/python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { throw 'A pinned build Python environment is required.' }
$output = Join-Path $projectRoot "artifacts/release/$Version-$Edition"
if (Test-Path -LiteralPath $output) { throw 'Immutable build directory already exists. Choose another version.' }
New-Item -ItemType Directory -Path $output -Force | Out-Null
function Run-Python([string[]]$Arguments) {
    & $Python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python build step failed ($LASTEXITCODE)." }
}
Run-Python -Arguments @('-m','pip','check')
Run-Python -Arguments @('-m','aster_release.build_support','--edition',$Edition,'--output',$output,'--version',$Version)
if (-not $SkipTests) { Run-Python -Arguments @('-m','pytest','-q') }
if ($SkipTests -and $Edition -ne 'ValidationOnly') { throw 'Distributable builds cannot skip source tests.' }
# Freeze from a new, minimal environment, not the development environment.
$buildEnvironment = Join-Path $output 'build-env'
Run-Python -Arguments @('-m','venv',$buildEnvironment)
$Python = Join-Path $buildEnvironment 'Scripts/python.exe'
Run-Python -Arguments @('-m','pip','install','--extra-index-url','https://download.pytorch.org/whl/cpu','-r','packaging/requirements-runtime.lock.txt','-r','packaging/requirements-build.lock.txt')
Run-Python -Arguments @('-m','pip','check')
foreach ($component in @('aster-launcher','aster-api','aster-web')) {
    Run-Python -Arguments @('-m','PyInstaller','--noconfirm','--distpath',"$output/frozen",'--workpath',"$output/work/$component","packaging/$component.spec")
}
Run-Python -Arguments @('packaging/stage-assets.py','--source',$projectRoot,'--output',"$output/portable",'--profile',"$output/profile.json",'--edition',$Edition,'--frozen',"$output/frozen")
Run-Python -Arguments @('packaging/verify-package.py',"$output/portable")
Run-Python -Arguments @('-m','aster_release.encoder_check',"$output/portable")
Write-Host "Verified $Edition build: $output/portable"
if ($Edition -eq 'ValidationOnly') { Write-Warning 'Local validation only: NOT approved for redistribution.' }
