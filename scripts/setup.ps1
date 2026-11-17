$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

$generatedPassword = $null

if (-not (Test-Path -LiteralPath "apps/api/.env")) {
    $secret = py -3.13 -c "import secrets; print(secrets.token_hex(32))"
    $generatedPassword = py -3.13 -c "import secrets; print(secrets.token_urlsafe(12))"
    $content = @"
PETROSENSE_ENVIRONMENT=development
PETROSENSE_SECRET_KEY=$secret
PETROSENSE_DATABASE_URL=sqlite:///./data/petrosense.db
PETROSENSE_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
PETROSENSE_ACCESS_TOKEN_MINUTES=15
PETROSENSE_REFRESH_TOKEN_DAYS=7
PETROSENSE_COOKIE_SECURE=false
PETROSENSE_DEMO_PASSWORD=$generatedPassword
PETROSENSE_LOG_LEVEL=INFO
"@
    Set-Content -LiteralPath "apps/api/.env" -Value $content -Encoding ASCII
    Write-Host "Created apps/api/.env with a generated secret and demo password."
}

if (-not (Test-Path -LiteralPath ".env")) {
    Copy-Item -LiteralPath "apps/api/.env" -Destination ".env"
    Write-Host "Created root .env for Docker Compose."
}

if (-not (Test-Path -LiteralPath "apps/api/.venv")) {
    py -3.13 -m venv "apps/api/.venv"
}

& "apps/api/.venv/Scripts/python.exe" -m pip install --upgrade pip
Push-Location -LiteralPath "apps/api"
try {
    & ".venv/Scripts/python.exe" -m pip install -e ".[dev]"
    & ".venv/Scripts/alembic.exe" upgrade head
    & ".venv/Scripts/python.exe" -m app.db.seed
}
finally {
    Pop-Location
}

npm install
& "apps/api/.venv/Scripts/python.exe" -m pip install -e "edge"
& "apps/api/.venv/Scripts/python.exe" -m pip install -e "ml"

Write-Host ""
Write-Host "Setup complete."
Write-Host "API:      cd apps/api; .venv\\Scripts\\python -m uvicorn app.main:app --reload"
Write-Host "Web:      npm run dev:web"
Write-Host "Verify:   powershell -File scripts/verify.ps1"
if ($null -ne $generatedPassword) {
    Write-Host "Demo password generated in apps/api/.env: $generatedPassword"
    Write-Host "Change it before any shared demonstration."
} else {
    Write-Host "Existing apps/api/.env retained. Read PETROSENSE_DEMO_PASSWORD from it if needed."
}
