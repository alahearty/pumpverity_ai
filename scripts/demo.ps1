# PumpVerity AI - one-click presentation launcher (Windows PowerShell)
#
#   powershell -ExecutionPolicy Bypass -File scripts/demo.ps1            # start everything
#   powershell -ExecutionPolicy Bypass -File scripts/demo.ps1 -Warmup    # + scripted history first
#   powershell -ExecutionPolicy Bypass -File scripts/demo.ps1 -Reset     # fresh database + model
#
# Opens three windows (API, web, simulated edge stream) and the browser. Close those windows,
# or run scripts/demo-stop.ps1, to stop. Requires scripts/setup.ps1 (or the manual setup) first.

param(
    [switch]$Reset,
    [switch]$Warmup,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$python = Join-Path $root "apps/api/.venv/Scripts/python.exe"
$envFile = Join-Path $root "apps/api/.env"
$apiBase = "http://127.0.0.1:8000/api/v1"

function Read-EnvValue([string]$key) {
    foreach ($line in Get-Content -LiteralPath $envFile) {
        if ($line -match "^\s*$key\s*=\s*(.+)\s*$") { return $Matches[1].Trim() }
    }
    return $null
}

function Test-Port([int]$port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect("localhost", $port); return $true } catch { return $false } finally { $client.Close() }
}

function Wait-Url([string]$url, [int]$seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -eq 200) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

if (-not (Test-Path -LiteralPath $python)) { throw "Python venv missing. Run scripts/setup.ps1 first." }
if (-not (Test-Path -LiteralPath $envFile)) { throw "apps/api/.env missing. Run scripts/setup.ps1 first." }
if (-not (Test-Path -LiteralPath (Join-Path $root "node_modules"))) { throw "node_modules missing. Run npm install." }
if ((Read-EnvValue "PETROSENSE_DEMO_MODE") -ne "true") {
    Write-Warning "PETROSENSE_DEMO_MODE=true is not set in apps/api/.env - the scenario panel will be hidden."
}
$password = Read-EnvValue "PETROSENSE_DEMO_PASSWORD"
if (-not $password) { throw "PETROSENSE_DEMO_PASSWORD is not set in apps/api/.env." }

foreach ($port in 8000, 5173) {
    if (Test-Port $port) { throw "Port $port is already in use. Run scripts/demo-stop.ps1 first." }
}

if ($Reset) {
    Write-Host "Resetting the demo database..." -ForegroundColor Yellow
    # Remove the SQLite WAL/SHM journals too, or a stale journal can be replayed into the new file.
    foreach ($suffix in "", "-wal", "-shm") {
        $file = Join-Path $root "apps/api/data/petrosense.db$suffix"
        if (Test-Path -LiteralPath $file) { Remove-Item -LiteralPath $file -Force }
    }
}

# Native tools log to stderr; in Windows PowerShell 5.1 that must not be treated as a failure.
function Invoke-Quiet([string]$exe, [string[]]$arguments, [string]$failure) {
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $exe @arguments 2>&1
        if ($LASTEXITCODE -ne 0) {
            $output | ForEach-Object { Write-Host "    $_" -ForegroundColor DarkGray }
            throw $failure
        }
    } finally {
        $ErrorActionPreference = $previous
    }
}

Write-Host "Applying migrations and seed data..." -ForegroundColor Cyan
Push-Location -LiteralPath "apps/api"
try {
    Invoke-Quiet ".venv/Scripts/alembic.exe" @("upgrade", "head") "Database migration failed."
    # --reset-passwords keeps the documented demo sign-in details valid on every launch.
    Invoke-Quiet ".venv/Scripts/python.exe" @("-m", "app.db.seed", "--reset-passwords") "Seeding failed."
} finally {
    Pop-Location
}

Write-Host "Starting the monitoring API on :8000..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'PumpVerity API'; Set-Location -LiteralPath '$root/apps/api'; .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
) | Out-Null
if (-not (Wait-Url "$apiBase/health" 60)) { throw "The API did not become healthy within 60 seconds." }
Write-Host "  API healthy." -ForegroundColor Green

# Make sure a validated edge model is active (trains the synthetic pipeline on first run).
$token = (Invoke-RestMethod -Method Post -Uri "$apiBase/auth/login" -ContentType "application/json" `
    -Body (@{ identifier = "researcher"; password = $password } | ConvertTo-Json)).access_token
$active = $null
try {
    $active = Invoke-RestMethod -Uri "$apiBase/models/active" -Headers @{ Authorization = "Bearer $token" }
} catch { }
# The API answers JSON null when no model is active; PowerShell 5.1 may not map that to $null.
if (-not ($active -and $active.id)) {
    Write-Host "No active model - training and registering the synthetic edge model (1-2 min)..." -ForegroundColor Cyan
    $env:PETROSENSE_ML_PASSWORD = $password
    Invoke-Quiet $python @("-m", "petrosense_ml.pipeline", "--register") "Model training/registration failed."
    Remove-Item Env:PETROSENSE_ML_PASSWORD
    $active = Invoke-RestMethod -Uri "$apiBase/models/active" -Headers @{ Authorization = "Bearer $token" }
    if (-not ($active -and $active.id)) { throw "Model registration finished but no model is active." }
}
Write-Host "  Edge model active: $($active.name) v$($active.version)" -ForegroundColor Green

Write-Host "Starting the web app on :5173..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'PumpVerity Web'; Set-Location -LiteralPath '$root'; npm run dev:web"
) | Out-Null

$driverArgs = "-m petrosense_edge.demo"
if ($Warmup -or $Reset) { $driverArgs += " --warmup" }
Write-Host "Starting the simulated edge stream..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle = 'PumpVerity Edge (simulated)'; Set-Location -LiteralPath '$root'; & '$python' $driverArgs"
) | Out-Null

if (-not (Wait-Url "http://localhost:5173" 60)) { Write-Warning "Web app is slow to start; refresh the browser in a moment." }

if (-not $NoBrowser) { Start-Process "http://localhost:5173" }

Write-Host ""
Write-Host "PumpVerity AI demo is running." -ForegroundColor Green
Write-Host "  Web:       http://localhost:5173"
Write-Host "  API docs:  http://localhost:8000/docs"
Write-Host "  Sign in:   engineer  (or admin)   password: $password"
Write-Host "  Control:   presenter bar at the bottom of the app - keys 1-5 switch scenario, P pauses"
Write-Host "  Stop:      powershell -File scripts/demo-stop.ps1"
