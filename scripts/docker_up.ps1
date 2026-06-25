<#
.SYNOPSIS
    Start VideoMind Agent Docker backend.
.DESCRIPTION
    Checks Docker availability, creates .env.docker if missing, then starts docker compose.
#>

param(
    [switch]$Help
)

if ($Help) {
    Write-Host "Usage: .\scripts\docker_up.ps1"
    Write-Host "Starts VideoMind backend via Docker Compose."
    exit 0
}

# Check Docker
try {
    $ver = docker --version 2>&1
    if (-not $?) { throw "Docker not found" }
    Write-Host "[OK] Docker: $ver"
} catch {
    Write-Host "[ERROR] Docker is not available. Please install Docker Desktop for Windows first."
    Write-Host "       https://docs.docker.com/desktop/setup/install/windows-install/"
    exit 1
}

# Check docker compose
try {
    docker compose version 2>&1 | Out-Null
    if (-not $?) { throw "docker compose not found" }
    Write-Host "[OK] docker compose available"
} catch {
    Write-Host "[ERROR] docker compose plugin is not available."
    Write-Host "       Please ensure Docker Desktop includes the compose plugin."
    exit 1
}

# Create .env.docker if not exists
$envFile = Join-Path (Split-Path $PSScriptRoot -Parent) ".env.docker"
$envExample = Join-Path (Split-Path $PSScriptRoot -Parent) ".env.docker.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "[INFO] Created .env.docker from .env.docker.example"
        Write-Host "[INFO] Edit .env.docker to customize settings (e.g., DEEPSEEK_API_KEY)"
    } else {
        Write-Host "[WARN] .env.docker.example not found. Creating minimal .env.docker"
@"
VIDEOMIND_DEVICE=cpu
VIDEOMIND_PLANNER_PROVIDER=rule
"@ | Out-File -FilePath $envFile -Encoding utf8
    }
} else {
    Write-Host "[OK] .env.docker already exists"
}

# Start docker compose
Write-Host ""
Write-Host "[INFO] Starting VideoMind backend..."
Write-Host "[INFO] This may take a few minutes on first run (building image + downloading deps)."
Write-Host ""

$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location $projectRoot
try {
    docker compose up -d --build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] docker compose failed with exit code $LASTEXITCODE"
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "[OK] VideoMind backend started!"
Write-Host "    Backend: http://127.0.0.1:8000"
Write-Host "    Health:  http://127.0.0.1:8000/health"
Write-Host "    Logs:    docker compose logs -f backend"
Write-Host ""
Write-Host "To stop: .\scripts\docker_down.ps1"
