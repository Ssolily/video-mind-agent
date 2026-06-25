<#
.SYNOPSIS
    Stop VideoMind Agent Docker backend.
#>

param([switch]$Help)
if ($Help) { Write-Host "Usage: .\scripts\docker_down.ps1"; exit 0 }

$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    docker compose down
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] VideoMind backend stopped."
    } else {
        Write-Host "[WARN] docker compose down returned exit code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}
