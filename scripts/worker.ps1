<#
.SYNOPSIS
    Start or manage the VideoMind background task worker.
.DESCRIPTION
    Starts the RQ-compatible in-process task worker for VideoMind Agent.
    The worker processes queued video analysis tasks.
.PARAMETER Stop
    Stop the worker process using PID file.
.PARAMETER Concurrency
    Number of parallel workers (default: 1).
.EXAMPLE
    .\scripts\worker.ps1
    .\scripts\worker.ps1 -Concurrency 2
    .\scripts\worker.ps1 -Stop
#>

param(
    [switch]$Stop,
    [int]$Concurrency = 1
)

$RootDir = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $RootDir "logs" "worker.pid"
$LogFile = Join-Path $RootDir "logs" "worker.log"

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

# Ensure logs directory
$null = New-Item -ItemType Directory -Path (Join-Path $RootDir "logs") -Force

if ($Stop) {
    if (Test-Path $PidFile) {
        $pid = Get-Content $PidFile
        Write-Host "Stopping worker (PID: $pid)..."
        try {
            Stop-Process -Id $pid -Force -ErrorAction Stop
            Write-Host "Worker stopped."
        } catch {
            Write-Host "Worker process not found (PID: $pid)"
        }
        Remove-Item $PidFile -Force
    } else {
        Write-Host "No worker PID file found at $PidFile"
    }
    exit
}

Write-Host "Starting VideoMind Worker (concurrency: $Concurrency)..."
Write-Host "Log: $LogFile"

# Start worker in background
$startScript = @"
from app.services import task_queue
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
task_queue.start_workers(num_workers=$Concurrency)
import time
try:
    while True:
        time.sleep(10)
except KeyboardInterrupt:
    task_queue.stop_workers()
"@

$logFile = $LogFile
$startScript | Out-File -Encoding utf8 -FilePath (Join-Path $RootDir "logs\_worker_script.py")

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $AgentPython
$psi.Arguments = "-u " + (Join-Path $RootDir "logs\_worker_script.py")
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.WorkingDirectory = $RootDir
$psi.CreateNoWindow = $true

$p = [System.Diagnostics.Process]::Start($psi)
$p.Id | Out-File -Encoding utf8 -FilePath $PidFile

Write-Host "Worker started (PID: $($p.Id))"
Write-Host "To stop: .\scripts\worker.ps1 -Stop"