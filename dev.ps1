<#
.SYNOPSIS
  VideoMind Agent -- Windows one-click startup script.
.DESCRIPTION
  Starts backend (uvicorn) and frontend (Vite) in separate PowerShell windows.
  Supports -Kill, -NoFrontend, -NoReload, -Port, -Production, -CondaEnv.
#>

param(
  [switch]$Kill,
  [switch]$NoFrontend,
  [switch]$NoReload,
  [int]$Port = 8000,
  [switch]$Production,
  [string]$CondaEnv = "agent"
)

$ScriptRoot = $PSScriptRoot
if (-not $ScriptRoot) { $ScriptRoot = Get-Location }

$LogsDir     = Join-Path $ScriptRoot "logs"
$BackendDir  = Join-Path $ScriptRoot "backend"
$FrontendDir = Join-Path $ScriptRoot "frontend"

$BackendPidFile = Join-Path $LogsDir "backend.pid"
$FrontendPidFile = Join-Path $LogsDir "frontend.pid"
$BackendLogFile  = Join-Path $LogsDir "backend.log"
$FrontendLogFile = Join-Path $LogsDir "frontend.log"
$StartupLogFile  = Join-Path $LogsDir "dev_startup.log"

$BackendPort = $Port
$FrontendPort = 5173

# ---- helpers ---------------------------------------------------------------
function Write-Log {
  param([string]$Message)
  $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
  if ($global:StartupLogFile) {
    Add-Content -Path $StartupLogFile -Value $line -Encoding UTF8
  }
  Write-Output $line
}

function Test-PortInUse {
  param([int]$PortNumber)
  $conn = netstat -ano | Select-String "LISTENING" | Select-String ":$PortNumber "
  return ($null -ne $conn)
}

function Get-PidOnPort {
  param([int]$PortNumber)
  $line = netstat -ano | Select-String "LISTENING" | Select-String ":$PortNumber "
  if ($line) {
    $parts = $line.ToString() -split '\s+'
    return $parts[-1]
  }
  return $null
}

# ---- Kill ------------------------------------------------------------------
if ($Kill) {
  Write-Host "=== Stopping VideoMind managed processes ===" -ForegroundColor Cyan
  $stopped = $false

  if (Test-Path $BackendPidFile) {
    $savedPid = Get-Content $BackendPidFile -Raw | ForEach-Object { $_.Trim() }
    if ($savedPid -and $savedPid.Length -gt 0) {
      if (Get-Process -Id $savedPid -ErrorAction SilentlyContinue) {
        Stop-Process -Id $savedPid -Force
        Write-Host "  Stopped backend (PID $savedPid)" -ForegroundColor Green
        $stopped = $true
      }
    }
    Remove-Item $BackendPidFile -Force -ErrorAction SilentlyContinue
  }

  if (Test-Path $FrontendPidFile) {
    $savedPid = Get-Content $FrontendPidFile -Raw | ForEach-Object { $_.Trim() }
    if ($savedPid -and $savedPid.Length -gt 0) {
      $proc = Get-Process -Id $savedPid -ErrorAction SilentlyContinue
      if ($proc) {
        Stop-Process -Id $savedPid -Force
        Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object {
          $_.Parent -eq (Get-Process -Id $savedPid)
        } | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "  Stopped frontend (PID $savedPid)" -ForegroundColor Green
        $stopped = $true
      }
    }
    Remove-Item $FrontendPidFile -Force -ErrorAction SilentlyContinue
  }

  if (-not $stopped) {
    Write-Host "  No managed processes found (PID files missing)." -ForegroundColor Yellow
    Write-Host "  Running python/node processes (skipped):" -ForegroundColor Gray
    Get-Process -Name "python", "node" -ErrorAction SilentlyContinue | ForEach-Object {
      Write-Host "    PID $($_.Id): $($_.ProcessName)" -ForegroundColor Gray
    }
  }

  Write-Host "=== Done ===" -ForegroundColor Cyan
  exit 0
}

# ---- Pre-flight checks -----------------------------------------------------
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VideoMind Agent -- Startup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
""

New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $ScriptRoot "data") -Force | Out-Null

$global:StartupLogFile = $StartupLogFile
Remove-Item $StartupLogFile -ErrorAction SilentlyContinue

Write-Log "=== VideoMind dev.ps1 startup ==="
Write-Log "Script root: $ScriptRoot"
Write-Log "Backend port: $BackendPort"
Write-Log "Conda env: $CondaEnv"
Write-Log "NoFrontend: $NoFrontend"
Write-Log "NoReload: $NoReload"
Write-Log "Production: $Production"

if (-not (Test-Path $BackendDir)) {
  Write-Log "ERROR: backend/ not found at $BackendDir"
  Write-Host "[FAIL] backend/ not found. Run from project root." -ForegroundColor Red
  exit 1
}
if (-not (Test-Path $FrontendDir)) {
  Write-Log "ERROR: frontend/ not found at $FrontendDir"
  Write-Host "[FAIL] frontend/ not found. Run from project root." -ForegroundColor Red
  exit 1
}

# Check conda
$condaAvailable = $false
try {
  $condaVer = conda --version 2>&1
  if ($LASTEXITCODE -eq 0) { $condaAvailable = $true; Write-Log "conda: $condaVer" }
} catch {}
if (-not $condaAvailable) {
  Write-Log "ERROR: conda not available"
  Write-Host "[FAIL] conda not available. Install conda first." -ForegroundColor Red
  exit 1
}

# Check conda env
$envExists = $false
try {
  $envs = conda env list 2>&1
  if ($envs -match $CondaEnv) { $envExists = $true; Write-Log "conda env '$CondaEnv' exists" }
} catch {}
if (-not $envExists) {
  Write-Log "ERROR: conda env '$CondaEnv' not found"
  Write-Host "[FAIL] conda env '$CondaEnv' not found. Run: conda env create -f environment.yml" -ForegroundColor Red
  exit 1
}

# Check Node/npm
try {
  $nodeVer = node --version 2>&1
  $npmVer = npm --version 2>&1
  Write-Log "Node: $nodeVer, npm: $npmVer"
} catch {
  Write-Log "ERROR: Node/npm not available"
  Write-Host "[FAIL] Node.js not found. Install Node.js first." -ForegroundColor Red
  exit 1
}

# Check ffmpeg/ffprobe
try {
  $ffmpegVer = ffmpeg -version 2>&1 | Select-Object -First 1
  $ffprobeVer = ffprobe -version 2>&1 | Select-Object -First 1
  Write-Log "ffmpeg: $ffmpegVer"
  Write-Log "ffprobe: $ffprobeVer"
} catch {
  Write-Log "WARNING: ffmpeg/ffprobe not found"
  Write-Host "[WARN] ffmpeg not found. Video processing will fail." -ForegroundColor Yellow
}

# Port check
if (Test-PortInUse $BackendPort) {
  $savedPid = Get-PidOnPort $BackendPort
  Write-Log "ERROR: Backend port $BackendPort in use by PID $savedPid"
  Write-Host "[FAIL] Backend port $BackendPort is in use by PID $savedPid" -ForegroundColor Red
  Write-Host "  Use -Kill to stop, or -Port <port> for a different port." -ForegroundColor Yellow
  exit 1
} else {
  Write-Log "Backend port $BackendPort free"
  Write-Host ("[OK]   Backend port " + $BackendPort + ": free") -ForegroundColor Green
}

if (-not $NoFrontend) {
  if (Test-PortInUse $FrontendPort) {
    $savedPid = Get-PidOnPort $FrontendPort
    Write-Log "ERROR: Frontend port $FrontendPort in use by PID $savedPid"
    Write-Host "[FAIL] Frontend port $FrontendPort is in use by PID $savedPid" -ForegroundColor Red
    Write-Host "  Use -Kill to stop managed services." -ForegroundColor Yellow
    exit 1
  } else {
    Write-Log "Frontend port $FrontendPort free"
    Write-Host ("[OK]   Frontend port " + $FrontendPort + ": free") -ForegroundColor Green
  }
}

# ---- Start Backend ---------------------------------------------------------
Write-Host ""
Write-Host "--- Starting Backend ---" -ForegroundColor Cyan

$reloadFlag = ""
if (-not $NoReload) { $reloadFlag = "--reload" }

$backendCmd = "Set-Location '$BackendDir'; conda activate $CondaEnv; uvicorn app.main:app $reloadFlag --host 0.0.0.0 --port $BackendPort 2>&1 | Tee-Object -FilePath '$BackendLogFile' -Append"
$backendArgs = @("-NoExit", "-Command", $backendCmd)

$backendProc = Start-Process powershell -WindowStyle Normal -ArgumentList $backendArgs -PassThru

$backendProc.Id | Out-File -FilePath $BackendPidFile -Encoding UTF8 -Force
Write-Log "Backend started (PID $($backendProc.Id))"
Write-Host "  Backend PID: $($backendProc.Id)" -ForegroundColor Green
Write-Host ("  Backend URL: http://127.0.0.1:" + $BackendPort) -ForegroundColor Green
Write-Host "  Backend log: $BackendLogFile" -ForegroundColor Gray

# ---- Health Check ----------------------------------------------------------
Start-Sleep -Seconds 3
$healthUrl = "http://127.0.0.1:" + $BackendPort + "/health"
Write-Host "  Health check: $healthUrl" -ForegroundColor Gray

$healthy = $false
for ($i = 0; $i -lt 20; $i++) {
  try {
    $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
    if ($resp.StatusCode -eq 200) {
      $healthy = $true
      Write-Log "Backend healthy (attempt $($i+1))"
      Write-Host ("  [OK]   Backend healthy after " + ($i+1) + "s") -ForegroundColor Green
      break
    }
  } catch { }
  Start-Sleep -Seconds 1
}

if (-not $healthy) {
  Write-Log "WARNING: Backend health check failed within 20s"
  Write-Host "  [WARN] Backend did not respond within 20s." -ForegroundColor Yellow
  Write-Host "  Check $BackendLogFile for details." -ForegroundColor Yellow
}

# ---- Start Frontend --------------------------------------------------------
if (-not $NoFrontend) {
  Write-Host ""
  Write-Host "--- Starting Frontend ---" -ForegroundColor Cyan

  if ($Production) {
    Write-Host "  Production mode: building frontend..." -ForegroundColor Gray
    $frontendCmd = "Set-Location '$FrontendDir'; npm run build --if-present; npm run preview 2>&1 | Tee-Object -FilePath '$FrontendLogFile' -Append"
  } else {
    $frontendCmd = "Set-Location '$FrontendDir'; npm run dev 2>&1 | Tee-Object -FilePath '$FrontendLogFile' -Append"
  }

  $frontendArgs = @("-NoExit", "-Command", $frontendCmd)
  $frontendProc = Start-Process powershell -WindowStyle Normal -ArgumentList $frontendArgs -PassThru

  $frontendProc.Id | Out-File -FilePath $FrontendPidFile -Encoding UTF8 -Force
  Write-Log "Frontend started (PID $($frontendProc.Id))"
  Write-Host "  Frontend PID: $($frontendProc.Id)" -ForegroundColor Green
  Write-Host ("  Frontend URL: http://127.0.0.1:" + $FrontendPort) -ForegroundColor Green
  Write-Host "  Frontend log: $FrontendLogFile" -ForegroundColor Gray
}

# ---- Summary ---------------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VideoMind Agent -- Started" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ("  Backend: http://127.0.0.1:" + $BackendPort) -ForegroundColor Green
if (-not $NoFrontend) {
  Write-Host ("  Frontend: http://127.0.0.1:" + $FrontendPort) -ForegroundColor Green
}
Write-Host "  Logs:     $LogsDir" -ForegroundColor Gray
Write-Host "  To stop:  .\dev.ps1 -Kill" -ForegroundColor Gray
Write-Host ""

Write-Log "=== Startup complete ==="
