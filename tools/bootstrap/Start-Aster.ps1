<#
  Start Aster from the source ZIP.

  Trust: release/bootstrap-pin.json in this source tree pins the exact SHA-256 of
  AsterSetup-Windows-x64.exe. The setup executable itself embeds the signed
  release lock that pins every model, runtime and library file it downloads.
  A downloaded file whose hash differs is deleted and never run.

  Parameters (for testing or offline use):
    -Mirror <url>      download the pinned setup from another base URL (hash still enforced)
    -SetupPath <file>  use an already downloaded AsterSetup-Windows-x64.exe (hash still enforced)
    -InstallDir <dir>  install location (default: %LOCALAPPDATA%\Programs\Aster)
    -Quiet             no windows (automation); setup runs with --quiet
    -SetupArgs <args>  extra arguments passed to setup
#>
param(
    [string]$Mirror = "",
    [string]$SetupPath = "",
    [string]$InstallDir = "",
    [switch]$Quiet,
    [string[]]$SetupArgs = @()
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 -bor [Net.SecurityProtocolType]::Tls13

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$pinPath = Join-Path $repoRoot "release\bootstrap-pin.json"
if (-not $InstallDir) { $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\Aster" }
$cacheDir = Join-Path $env:LOCALAPPDATA "Aster\bootstrap"

function Show-Message([string]$text, [string]$title = "Aster") {
    if ($Quiet) { Write-Host $text; return }
    Add-Type -AssemblyName System.Windows.Forms
    [void][System.Windows.Forms.MessageBox]::Show($text, $title)
}

function Start-InstalledAster {
    $currentPath = Join-Path $InstallDir "current.json"
    if (-not (Test-Path -LiteralPath $currentPath)) { return $false }
    try { $current = Get-Content -LiteralPath $currentPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { return $false }
    $exe = Join-Path $InstallDir ("versions\" + $current.version + "\Aster.exe")
    if (-not (Test-Path -LiteralPath $exe)) { return $false }
    Start-Process -FilePath $exe -WorkingDirectory (Split-Path -Parent $exe)
    return $true
}

if (Start-InstalledAster) { exit 0 }

if (-not (Test-Path -LiteralPath $pinPath)) {
    Show-Message "This copy of Aster does not name a release to install (release\bootstrap-pin.json is missing). Download the source ZIP again from https://github.com/AyushM1701/ASTER-AI or use AsterSetup-Windows-x64.exe from the Releases page."
    exit 1
}
$pin = Get-Content -LiteralPath $pinPath -Raw -Encoding UTF8 | ConvertFrom-Json
$sizeMb = [math]::Round($pin.bytes / 1MB, 1)

function Confirm-FirstRun {
    if ($Quiet) { return $true }
    Add-Type -AssemblyName System.Windows.Forms
    $text = "Aster is not installed on this computer yet.`r`n`r`n" +
            "Aster will download its verified setup program ($sizeMb MB) and then install the local AI models, text reader, " +
            "X-ray checker and medical reference library. The total download is several gigabytes and can take from about " +
            "15 minutes to over an hour, depending on your connection. An internet connection is needed only for this first setup; " +
            "afterwards Aster works offline.`r`n`r`nNo account, API key, Python, Docker or other software is needed. Continue?"
    $answer = [System.Windows.Forms.MessageBox]::Show($text, "Start Aster - first-time setup", "OKCancel", "Information")
    return $answer -eq [System.Windows.Forms.DialogResult]::OK
}

function Test-Pinned([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) { return $false }
    if ((Get-Item -LiteralPath $path).Length -ne [int64]$pin.bytes) { return $false }
    return ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $pin.sha256)
}

function Get-PinnedSetup([string]$target) {
    $urls = @()
    if ($Mirror) { $urls += ($Mirror.TrimEnd("/") + "/" + $pin.file) }
    $urls += $pin.url
    $partial = $target + ".partial"
    $form = $null; $bar = $null; $label = $null; $script:cancelled = $false
    if (-not $Quiet) {
        Add-Type -AssemblyName System.Windows.Forms
        $form = New-Object System.Windows.Forms.Form
        $form.Text = "Start Aster - downloading setup"; $form.Width = 520; $form.Height = 180; $form.StartPosition = "CenterScreen"
        $form.FormBorderStyle = "FixedDialog"; $form.MaximizeBox = $false
        $label = New-Object System.Windows.Forms.Label
        $label.Left = 16; $label.Top = 14; $label.Width = 470; $label.Height = 40; $label.Text = "Connecting..."
        $bar = New-Object System.Windows.Forms.ProgressBar
        $bar.Left = 16; $bar.Top = 60; $bar.Width = 470; $bar.Height = 22; $bar.Maximum = 1000
        $cancel = New-Object System.Windows.Forms.Button
        $cancel.Text = "Cancel"; $cancel.Left = 396; $cancel.Top = 94; $cancel.Width = 90
        $cancel.Add_Click({ $script:cancelled = $true })
        $form.Controls.AddRange(@($label, $bar, $cancel))
        $form.Show(); [System.Windows.Forms.Application]::DoEvents()
    }
    $lastError = ""
    foreach ($url in $urls) {
        for ($attempt = 1; $attempt -le 4; $attempt++) {
            try {
                $start = 0
                if (Test-Path -LiteralPath $partial) { $start = (Get-Item -LiteralPath $partial).Length }
                if ($start -ge [int64]$pin.bytes) { Remove-Item -LiteralPath $partial -Force; $start = 0 }
                $request = [System.Net.HttpWebRequest]::Create($url)
                $request.UserAgent = "AsterBootstrap/1"
                $request.Timeout = 60000; $request.ReadWriteTimeout = 60000
                if ($start -gt 0) { $request.AddRange([int64]$start) }
                $response = $request.GetResponse()
                if ($start -gt 0 -and [int]$response.StatusCode -ne 206) { $start = 0 }
                $stream = $response.GetResponseStream()
                $mode = if ($start -gt 0) { [System.IO.FileMode]::Append } else { [System.IO.FileMode]::Create }
                $file = New-Object System.IO.FileStream($partial, $mode, [System.IO.FileAccess]::Write)
                $buffer = New-Object byte[] 1048576
                $done = $start
                try {
                    while (($read = $stream.Read($buffer, 0, $buffer.Length)) -gt 0) {
                        if ($script:cancelled) { throw "cancelled" }
                        $file.Write($buffer, 0, $read)
                        $done += $read
                        if ($done -gt [int64]$pin.bytes) { throw "The download is larger than expected." }
                        if ($bar) {
                            $bar.Value = [int](1000 * $done / [int64]$pin.bytes)
                            $label.Text = ("Downloading Aster setup: {0:N1} of {1:N1} MB" -f ($done / 1MB), ($pin.bytes / 1MB))
                            [System.Windows.Forms.Application]::DoEvents()
                        }
                    }
                } finally { $file.Close(); $stream.Close(); $response.Close() }
                if (Test-Pinned $partial) {
                    Move-Item -LiteralPath $partial -Destination $target -Force
                    if ($form) { $form.Close() }
                    return $true
                }
                Remove-Item -LiteralPath $partial -Force -ErrorAction SilentlyContinue
                $lastError = "The downloaded setup did not match the verified fingerprint and was deleted."
            } catch {
                if ($script:cancelled -or "$_" -eq "cancelled") { if ($form) { $form.Close() }; return $false }
                $lastError = "$($_.Exception.Message)"
                if ($lastError -match "\(404\)") {
                    $lastError = "The pinned release $($pin.version) is not available at $url yet (HTTP 404)."
                    break
                }
                Start-Sleep -Seconds ([math]::Min(20, [math]::Pow(2, $attempt)))
            }
        }
    }
    if ($form) { $form.Close() }
    throw $lastError
}

if (-not (Confirm-FirstRun)) { exit 0 }
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null
$setup = Join-Path $cacheDir $pin.file
try {
    if ($SetupPath) {
        if (-not (Test-Pinned $SetupPath)) { throw "The provided setup file does not match the verified fingerprint." }
        Copy-Item -LiteralPath $SetupPath -Destination $setup -Force
    } elseif (-not (Test-Pinned $setup)) {
        if (-not (Get-PinnedSetup $setup)) { Show-Message "Setup was cancelled. Run Start Aster again to continue; the partial download is kept."; exit 0 }
    }
    if (-not (Test-Pinned $setup)) { throw "The setup file failed verification." }
} catch {
    Show-Message ("Aster could not download its setup program.`r`n`r`n" + $_ + "`r`n`r`nCheck your internet connection and run Start Aster again. If this continues, download AsterSetup-Windows-x64.exe from https://github.com/AyushM1701/ASTER-AI/releases.")
    exit 1
}
$arguments = @("--install-dir", $InstallDir)
if ($Mirror) { $arguments += @("--mirror", $Mirror) }
if ($Quiet) { $arguments += @("--quiet", "--launch") } else { $arguments += "--auto" }
$arguments += $SetupArgs
$quoted = $arguments | ForEach-Object { if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ } }
# Wait for setup itself only. Start-Process -Wait would also wait for every process setup starts,
# including Aster after "Launch", which kept this window open for as long as Aster ran.
$process = Start-Process -FilePath $setup -ArgumentList ($quoted -join " ") -PassThru
$null = $process.Handle  # keep a handle so ExitCode is available after the process ends
$process.WaitForExit()
exit $process.ExitCode
