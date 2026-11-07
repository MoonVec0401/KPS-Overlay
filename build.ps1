$ErrorActionPreference = "Stop"
$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectDir

python -m pip install --disable-pip-version-check pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Failed to install PyInstaller (exit code $LASTEXITCODE)" }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name KPSOverlay `
  --add-data "assets\ShiKeMengZhiKeAiTi\ShiKeMengZhiKeAiTi-2.ttf;assets\ShiKeMengZhiKeAiTi" `
  kps_overlay.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit code $LASTEXITCODE)" }
python -m PyInstaller --noconfirm --clean --onefile --windowed --name ExitKPSOverlay exit_overlay.py
if ($LASTEXITCODE -ne 0) { throw "Exit tool build failed (exit code $LASTEXITCODE)" }
Copy-Item -LiteralPath (Join-Path $projectDir "config.json") -Destination (Join-Path $projectDir "dist\config.json") -Force

Write-Host "Build complete: $projectDir\dist\KPSOverlay.exe and ExitKPSOverlay.exe"
