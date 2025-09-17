Param(
  [switch]$OpenBrowser = $true
)

$ErrorActionPreference = 'Stop'

function Require-Cmd($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    Write-Error "Command '$name' not found in PATH. Please install it first."
    exit 1
  }
}

$root = $PSScriptRoot
$serverDir = Join-Path $root 'server'

Write-Host "== Checking prerequisites =="
Require-Cmd node
Require-Cmd npm
Require-Cmd uv

if (-not (Test-Path $serverDir)) {
  Write-Error "Missing directory: $serverDir"
  exit 1
}

Write-Host "== Frontend: install deps if needed =="
$nodeModules = Join-Path $root 'node_modules'
if (-not (Test-Path $nodeModules)) {
  Write-Host "node_modules not found. Running: npm ci"
  Start-Process -FilePath 'npm' -ArgumentList @('ci') -WorkingDirectory $root -NoNewWindow -Wait
} else {
  Write-Host "node_modules exists. Skipping npm ci."
}

Write-Host "== Backend: uv sync =="
$pyproject = Join-Path $serverDir 'pyproject.toml'
if (Test-Path $pyproject) {
  Start-Process -FilePath 'uv' -ArgumentList @('sync') -WorkingDirectory $serverDir -NoNewWindow -Wait
} else {
  Write-Warning "pyproject.toml not found under server/. Skipping uv sync."
}

Write-Host "== Starting backend (uvicorn on http://localhost:8000) =="
$beCmd = "Set-Location `"$serverDir`"; uv run uvicorn main:app --reload --port 8000"
Start-Process -FilePath 'powershell' -ArgumentList '-NoExit','-NoProfile','-Command',$beCmd | Out-Null

Write-Host "== Starting frontend (Vite on http://localhost:5173) =="
$feCmd = "Set-Location `"$root`"; npm run dev"
Start-Process -FilePath 'powershell' -ArgumentList '-NoExit','-NoProfile','-Command',$feCmd | Out-Null

if ($OpenBrowser) {
  Start-Process 'http://localhost:5173'
}

Write-Host "All set. Frontend and backend are starting in separate windows."
