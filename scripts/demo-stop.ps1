# Stops the PumpVerity AI demo processes started by scripts/demo.ps1.
$ErrorActionPreference = "Continue"

foreach ($port in 8000, 5173) {
    $owners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($owner in $owners) {
        Write-Host "Stopping process $owner on port $port"
        Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue
    }
}

Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*petrosense_edge.demo*" } |
    ForEach-Object {
        Write-Host "Stopping demo driver $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

Write-Host "Demo stopped."
