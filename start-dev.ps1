# Start LeafScan frontend + backend for local and phone (LAN) testing.
# Usage: .\start-dev.ps1

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$BackendActivate = Join-Path $Backend ".venv\Scripts\Activate.ps1"
$BackendPython = Join-Path $Backend ".venv\Scripts\python.exe"
$FrontendNodeModules = Join-Path $Frontend "node_modules"
$RequiredArtifacts = @(
  (Join-Path $Backend "models\hybrid_effnet_mobilenet_distill_final.weights.h5"),
  (Join-Path $Backend "models\leaf_gate.weights.h5"),
  (Join-Path $Backend "app\data\class_labels.json")
)

function Stop-WithHelp {
  param(
    [string]$Reason,
    [string[]]$FixCommands
  )
  Write-Host ""
  Write-Host "Cannot start LeafScan: $Reason" -ForegroundColor Red
  Write-Host "Fix:" -ForegroundColor Yellow
  foreach ($Cmd in $FixCommands) {
    Write-Host "  $Cmd" -ForegroundColor Yellow
  }
  exit 1
}

if (-not (Test-Path $BackendActivate) -or -not (Test-Path $BackendPython)) {
  Stop-WithHelp `
    -Reason "Backend virtual environment not found." `
    -FixCommands @(
      "From repo root, run: .\setup-dev.ps1",
      "Or manually:",
      "  cd .\backend",
      "  py -3.11 -m venv .venv",
      "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    )
}

if (-not (Test-Path $FrontendNodeModules)) {
  Stop-WithHelp `
    -Reason "Frontend dependencies are missing (node_modules)." `
    -FixCommands @(
      "From repo root, run: .\setup-dev.ps1",
      "Or manually:",
      "  cd .\frontend",
      "  npm install"
    )
}

$MissingArtifacts = @()
foreach ($Artifact in $RequiredArtifacts) {
  if (-not (Test-Path $Artifact)) {
    $MissingArtifacts += $Artifact
  }
}
if ($MissingArtifacts.Count -gt 0) {
  $Fix = @("Copy the missing files into this repo, then rerun .\start-dev.ps1")
  $Fix += ($MissingArtifacts | ForEach-Object { "missing: $_" })
  Stop-WithHelp -Reason "Required model/class-label artifacts are missing." -FixCommands $Fix
}

Write-Host "Starting LeafScan backend (0.0.0.0:8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$Backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
)

Start-Sleep -Seconds 2

Write-Host "Starting LeafScan frontend (0.0.0.0:3000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "cd '$Frontend'; npm run dev"
)

Write-Host ""
Write-Host "PC:     http://localhost:3000" -ForegroundColor Cyan
Write-Host "Phone:  http://<your-lan-ip>:3000  (same Wi-Fi; run ipconfig for IPv4)" -ForegroundColor Cyan
Write-Host ""
Write-Host "If Analyze fails on phone, ensure the backend terminal is running (port 8000 on this PC only)." -ForegroundColor Yellow
