<#
.SYNOPSIS
    View VideoMind Agent Docker logs.
.DESCRIPTION
    Default: follow backend logs. Use -Tail N to show last N lines.
#>

param(
    [int]$Tail = 0,
    [switch]$Help
)
if ($Help) { Write-Host "Usage: .\scripts\docker_logs.ps1 [-Tail 100]"; exit 0 }

$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    if ($Tail -gt 0) {
        docker compose logs --tail $Tail backend
    } else {
        docker compose logs -f backend
    }
} finally {
    Pop-Location
}
