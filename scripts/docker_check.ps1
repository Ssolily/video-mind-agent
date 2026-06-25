<#
.SYNOPSIS
    Check VideoMind Agent Docker status.
.DESCRIPTION
    Checks docker compose status, backend /health, and volume mounts.
#>

param([switch]$Help)
if ($Help) { Write-Host "Usage: .\scripts\docker_check.ps1"; exit 0 }

$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    Write-Host "=== Docker Compose Status ==="
    docker compose ps

    Write-Host ""
    Write-Host "=== Backend Health Check ==="
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5
        if ($resp.StatusCode -eq 200) {
            Write-Host "[OK] Backend is healthy (HTTP 200)"
        } else {
            Write-Host "[WARN] Backend returned HTTP $($resp.StatusCode)"
        }
    } catch {
        Write-Host "[WARN] Backend health check failed: $_"
    }

    Write-Host ""
    Write-Host "=== Volume Mounts ==="
    docker compose inspect backend | python -c "import sys,json; d=json.load(sys.stdin); m=d[0]['Mounts']; [print(f'  {x["Type"]}: {x["Source"]} -> {x["Destination"]}') for x in m]" 2>$null

    Write-Host ""
    Write-Host "=== Data Directory (Host) ==="
    $dataDir = Join-Path $projectRoot "data"
    if (Test-Path $dataDir) {
        $items = Get-ChildItem $dataDir -Directory
        Write-Host "  $dataDir"
        foreach ($item in $items) {
            Write-Host "  - $($item.Name)/"
        }
    } else {
        Write-Host "  (not created yet)"
    }
} finally {
    Pop-Location
}
