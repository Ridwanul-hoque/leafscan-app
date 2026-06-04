# Run this script as Administrator if you need direct phone → :8000 access.
# Normal phone testing uses the Next.js /api proxy on port 3000 instead.
# Usage: Right-click PowerShell → Run as administrator, then:
#   cd "l:\BracU\Thesis App"
#   .\allow-firewall.ps1

$ErrorActionPreference = "Stop"

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Host "Re-run this script in an elevated (Administrator) PowerShell." -ForegroundColor Red
  exit 1
}

$ruleName = "LeafScan API 8000"
$existing = netsh advfirewall firewall show rule name="$ruleName" 2>$null
if ($LASTEXITCODE -eq 0) {
  Write-Host "Firewall rule '$ruleName' already exists." -ForegroundColor Yellow
} else {
  netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=8000 profile=private enable=yes | Out-Null
  Write-Host "Added inbound firewall rule for TCP port 8000 (Private networks)." -ForegroundColor Green
}

$venvPython = Join-Path $PSScriptRoot "backend\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
  $progRule = "LeafScan Python venv"
  netsh advfirewall firewall add rule name="$progRule" dir=in action=allow program="$venvPython" profile=private enable=yes | Out-Null
  Write-Host "Allowed venv Python through firewall: $venvPython" -ForegroundColor Green
}

Write-Host "Done. Phone testing via http://<lan-ip>:3000 does not require port 8000 open." -ForegroundColor Cyan
