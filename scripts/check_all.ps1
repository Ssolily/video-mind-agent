<#
.SYNOPSIS
    Run full regression check for VideoMind Agent.
.DESCRIPTION
    Checks compileall, backend pytest, frontend typecheck, test:run, and build.
    Returns non-zero exit code on any failure.
.PARAMETER SkipFrontendTests
    Skip frontend npm run test:run.
.PARAMETER SkipBuild
    Skip frontend npm run build.
.PARAMETER BackendOnly
    Only run backend checks (compileall + pytest). Implies -SkipFrontendTests -SkipBuild.
.EXAMPLE
    .\scripts\check_all.ps1
    .\scripts\check_all.ps1 -BackendOnly
    .\scripts\check_all.ps1 -SkipFrontendTests
#>

param(
    [switch]$SkipFrontendTests,
    [switch]$SkipBuild,
    [switch]$BackendOnly
)

$ErrorActionPreference = "Stop"
$ExitCode = 0

if ($BackendOnly) {
    $SkipFrontendTests = $true
    $SkipBuild = $true
}

$RootDir = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

# Resolve agent python dynamically to avoid hardcoded Windows paths
$AgentPython = & {
    $condaExe = Get-Command "conda" -ErrorAction SilentlyContinue
    if ($condaExe) {
        try {
            $envs = & conda info --envs --json 2>$null | ConvertFrom-Json
            $agentPath = $envs.envs | Where-Object { $_ -match '[\\/]agent$' } | Select-Object -First 1
            if ($agentPath) { Join-Path $agentPath "python.exe" } else { "python" }
        } catch { "python" }
    } else { "python" }
}

$PassedCount = 0
$FailedCount = 0

function Run-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "`n" -NoNewline
    Write-Host "════════════════════════════════════════════" -ForegroundColor DarkGray
    Write-Host "  Step: $Name" -ForegroundColor Cyan
    Write-Host "════════════════════════════════════════════" -ForegroundColor DarkGray
    try {
        & $Block
        Write-Host "  ✅ $Name — PASSED" -ForegroundColor Green
        $script:PassedCount++
    } catch {
        Write-Host "  ❌ $Name — FAILED" -ForegroundColor Red
        Write-Host "  Error: $_" -ForegroundColor Red
        $script:FailedCount++
        $script:ExitCode = 1
    }
}

# 1. compileall
Run-Step -Name "compileall backend/app scripts" -Block {
    & $AgentPython -m compileall "$RootDir\backend\app" "$RootDir\scripts" 2>&1 | ForEach-Object { Write-Host "    $_" }
    if ($LASTEXITCODE -ne 0) { throw "compileall failed" }
}

# 2. Backend pytest
Run-Step -Name "backend pytest" -Block {
    Push-Location $BackendDir
    & $AgentPython -m pytest -ra -q 2>&1 | ForEach-Object { Write-Host "    $_" }
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
    Pop-Location
}

if (-not $SkipFrontendTests) {
    # 3. Frontend typecheck
    Run-Step -Name "frontend typecheck" -Block {
        Push-Location $FrontendDir
        npm run typecheck 2>&1 | ForEach-Object { Write-Host "    $_" }
        if ($LASTEXITCODE -ne 0) { throw "typecheck failed" }
        Pop-Location
    }

    # 4. Frontend test:run
    Run-Step -Name "frontend test:run" -Block {
        Push-Location $FrontendDir
        npm run test:run 2>&1 | ForEach-Object { Write-Host "    $_" }
        if ($LASTEXITCODE -ne 0) { throw "test:run failed" }
        Pop-Location
    }
}

if (-not $SkipBuild) {
    # 5. Frontend build
    Run-Step -Name "frontend build" -Block {
        Push-Location $FrontendDir
        npm run build 2>&1 | ForEach-Object { Write-Host "    $_" }
        if ($LASTEXITCODE -ne 0) { throw "build failed" }
        Pop-Location
    }
}

Write-Host "`n"
Write-Host "════════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host "  REGRESSION SUMMARY" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════" -ForegroundColor DarkGray
Write-Host "  Passed: $PassedCount  Failed: $FailedCount" -ForegroundColor $(if ($FailedCount -eq 0) { "Green" } else { "Red" })
Write-Host "  Overall: $(if ($ExitCode -eq 0) { '✅ PASSED' } else { '❌ FAILED' })" -ForegroundColor $(if ($ExitCode -eq 0) { "Green" } else { "Red" })
Write-Host "════════════════════════════════════════════" -ForegroundColor DarkGray

exit $ExitCode