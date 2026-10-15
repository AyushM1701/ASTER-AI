@echo off
rem Start Aster from a downloaded GitHub source ZIP. No Python, Docker or other tools are needed.
rem First run: downloads and verifies the pinned Aster setup, which installs everything automatically.
rem Later runs: starts the installed Aster (works offline).
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\bootstrap\Start-Aster.ps1" %*
if errorlevel 1 (
  echo.
  echo Aster could not start. See the message above, then press any key to close this window.
  pause >nul
)
endlocal
