$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

Push-Location -LiteralPath "apps/api"
try {
    Write-Host "Running API lint..."
    & ".venv/Scripts/ruff.exe" check app tests
    if ($LASTEXITCODE -ne 0) { throw "API lint failed." }

    Write-Host "Running API tests..."
    & ".venv/Scripts/python.exe" -m pytest
    if ($LASTEXITCODE -ne 0) { throw "API tests failed." }
}
finally {
    Pop-Location
}

Write-Host "Running edge lint..."
& "apps/api/.venv/Scripts/ruff.exe" check edge/petrosense_edge edge/tests
if ($LASTEXITCODE -ne 0) { throw "Edge lint failed." }

Write-Host "Running edge tests..."
& "apps/api/.venv/Scripts/python.exe" -m pytest edge/tests
if ($LASTEXITCODE -ne 0) { throw "Edge tests failed." }

Write-Host "Running ML lint..."
& "apps/api/.venv/Scripts/ruff.exe" check ml/petrosense_ml ml/tests
if ($LASTEXITCODE -ne 0) { throw "ML lint failed." }

Write-Host "Running ML pipeline tests..."
& "apps/api/.venv/Scripts/python.exe" -m pytest ml/tests
if ($LASTEXITCODE -ne 0) { throw "ML tests failed." }

Write-Host "Running web lint..."
npm run lint --workspace @petrosense/web
if ($LASTEXITCODE -ne 0) { throw "Web lint failed." }

Write-Host "Running web tests..."
npm run test --workspace @petrosense/web
if ($LASTEXITCODE -ne 0) { throw "Web tests failed." }

Write-Host "Running web production build..."
npm run build --workspace @petrosense/web
if ($LASTEXITCODE -ne 0) { throw "Web build failed." }

Write-Host ""
Write-Host "Static verification passed."
Write-Host "Playwright requires the API and web servers to be running; see README.md."
