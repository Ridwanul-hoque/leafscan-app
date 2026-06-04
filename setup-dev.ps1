# One-time setup for a fresh Windows PC.
# Usage: .\setup-dev.ps1

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$BackendVenv = Join-Path $Backend ".venv"
$BackendActivate = Join-Path $BackendVenv "Scripts\Activate.ps1"
$BackendPython = Join-Path $BackendVenv "Scripts\python.exe"
$FrontendNodeModules = Join-Path $Frontend "node_modules"

$RequiredFiles = @(
  (Join-Path $Backend "models\hybrid_effnet_mobilenet_distill_final.weights.h5"),
  (Join-Path $Backend "models\leaf_gate.weights.h5"),
  (Join-Path $Backend "app\data\class_labels.json")
)

function Fail-And-Exit {
  param([string]$Message)
  Write-Host ""
  Write-Host "Setup failed: $Message" -ForegroundColor Red
  exit 1
}

Write-Host "LeafScan setup (fresh PC)" -ForegroundColor Green
Write-Host "Repo root: $Root"

# Tool checks
try {
  & py -3.11 --version | Out-Null
} catch {
  Fail-And-Exit "Python 3.11 is required. Install it first (example: winget install Python.Python.3.11)."
}

try {
  & node --version | Out-Null
  & npm --version | Out-Null
} catch {
  Fail-And-Exit "Node.js + npm are required. Install Node.js 20 LTS and reopen PowerShell."
}

# Backend venv
if (-not (Test-Path $BackendPython)) {
  Write-Host ""
  Write-Host "Creating backend venv with Python 3.11..." -ForegroundColor Yellow
  Push-Location $Backend
  try {
    & py -3.11 -m venv .venv
  } finally {
    Pop-Location
  }
} else {
  Write-Host "Backend venv already exists." -ForegroundColor DarkGray
}

# Backend deps
Write-Host ""
Write-Host "Installing backend dependencies..." -ForegroundColor Yellow
Push-Location $Backend
try {
  & $BackendPython -m pip install --upgrade pip
  & $BackendPython -m pip install -r requirements.txt
} finally {
  Pop-Location
}

# Env files
$BackendEnv = Join-Path $Backend ".env"
$BackendEnvExample = Join-Path $Backend ".env.example"
if (-not (Test-Path $BackendEnv) -and (Test-Path $BackendEnvExample)) {
  Copy-Item $BackendEnvExample $BackendEnv
  Write-Host "Created backend/.env from .env.example" -ForegroundColor Cyan
}

$FrontendEnv = Join-Path $Frontend ".env.local"
$FrontendEnvExample = Join-Path $Frontend ".env.local.example"
if (-not (Test-Path $FrontendEnv) -and (Test-Path $FrontendEnvExample)) {
  Copy-Item $FrontendEnvExample $FrontendEnv
  Write-Host "Created frontend/.env.local from .env.local.example" -ForegroundColor Cyan
}

# Frontend deps
Write-Host ""
if (-not (Test-Path $FrontendNodeModules)) {
  Write-Host "Installing frontend dependencies..." -ForegroundColor Yellow
} else {
  Write-Host "Refreshing frontend dependencies (npm install)..." -ForegroundColor Yellow
}
Push-Location $Frontend
try {
  & npm install
} finally {
  Pop-Location
}

# Required artifact checks
$Missing = @()
foreach ($Path in $RequiredFiles) {
  if (-not (Test-Path $Path)) {
    $Missing += $Path
  }
}

if ($Missing.Count -gt 0) {
  Write-Host ""
  Write-Host "Missing required files:" -ForegroundColor Red
  foreach ($Item in $Missing) {
    Write-Host "  - $Item" -ForegroundColor Red
  }
  Write-Host ""
  Write-Host "Copy these files into the project before running start-dev.ps1." -ForegroundColor Yellow
  exit 1
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Next: run .\start-dev.ps1" -ForegroundColor Cyan
