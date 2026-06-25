<#
.SYNOPSIS
    Create a VideoMind Agent release package via PowerShell.
.DESCRIPTION
    Copies backend, scripts, docs, Docker files, and README into a timestamped release directory under dist/.
.PARAMETER DryRun
    Preview what will be included without copying any files.
.PARAMETER Zip
    Create a .zip archive of the release.
.PARAMETER Output
    Custom output directory (default: dist/).
.EXAMPLE
    .\scripts\make_release.ps1 -DryRun
    .\scripts\make_release.ps1 -Zip
    .\scripts\make_release.ps1 -Output .\my-release
#>
param(
    [switch]$DryRun,
    [switch]$Zip,
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = "D:\Agent\video-mind-agent"
$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutputName = "video-mind-agent-release-$Timestamp"

if ($Output) {
    $OutputDir = Join-Path -Path (Resolve-Path $Output) -ChildPath $OutputName
} else {
    $distDir = Join-Path $RepoRoot "dist"
    if (-not (Test-Path $distDir)) { New-Item -ItemType Directory -Path $distDir -Force | Out-Null }
    $OutputDir = Join-Path $distDir $OutputName
}

$IncludePaths = @(
    "backend",`r`n    "frontend",
    "scripts",
    "docs",
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    ".env.example",
    ".env.docker.example",
    "README.md",
    "AGENTS.md"
)

$ExcludeDirs = @(
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".git", "data", "logs",
    "test_tmp", ".pytest_tmp", "venv", ".venv", "env", ".env",
    "dist", "models", "sam2", "tools", "frontend/dist"
)

$ExcludeExts = @(".pyc", ".pyo", ".pt", ".pth", ".bin", ".onnx",
                 ".log", ".mp4", ".mov", ".avi", ".mkv", ".webm",
                 ".zip", ".tar.gz", ".tgz", ".wav", ".mp3")

$ExcludeFiles = @(".env", ".DS_Store", "Thumbs.db", "yolo11n.pt", "package-lock.json", "PROJECT_AUDIT.md")

function Should-Exclude {
    param([string]$RelPath)
    $parts = $RelPath -split "[\\/]"
    foreach ($part in $parts) {
        if ($part -in $ExcludeDirs) { return $true }
    }
    $name = $parts[-1]
    if ($name -in $ExcludeFiles) { return $true }
    $ext = [System.IO.Path]::GetExtension($name).ToLower()
    if ($ext -in $ExcludeExts) { return $true }
    # Exclude P*_REPORT.md and audit files
    if ($name -match "^P\d.*_REPORT\.md$") { return $true }
    if ($name -match "^P\d.*_DRAFT\.md$") { return $true }
    if ($name -eq "HIGHLIGHT_REFACTOR_REPORT.md") { return $true }
    if ($name -eq "PROJECT_AUDIT.md") { return $true }
    return $false
}

# Collect files
$files = @()
foreach ($p in $IncludePaths) {
    $full = Join-Path $RepoRoot $p
    if (-not (Test-Path $full)) {
        Write-Host "  [WARN] $p does not exist, skipping" -ForegroundColor Yellow
        continue
    }
    if (Test-Path -Path $full -PathType Container) {
        Get-ChildItem -Path $full -Recurse -File | ForEach-Object {
            $rel = $_.FullName.Substring($RepoRoot.Length + 1)
            if (-not (Should-Exclude $rel)) { $files += $_ }
        }
    } else {
        $rel = $p
        if (-not (Should-Exclude $rel)) { $files += Get-Item $full }
    }
}

$totalSize = ($files | ForEach-Object { $_.Length } | Measure-Object -Sum).Sum

function Format-Size {
    param([long]$Bytes)
    if ($Bytes -gt 1GB) { return "{0:N2} GB" -f ($Bytes / 1GB) }
    elseif ($Bytes -gt 1MB) { return "{0:N2} MB" -f ($Bytes / 1MB) }
    elseif ($Bytes -gt 1KB) { return "{0:N1} KB" -f ($Bytes / 1KB) }
    else { return "$Bytes B" }
}

Write-Host "=== VideoMind Agent Release Packaging ===" -ForegroundColor Cyan
Write-Host "  Source: $RepoRoot"
Write-Host "  Output: $OutputDir"
Write-Host "  Mode:   $($(if ($DryRun) { 'DRY RUN' } else { 'CREATE' }))"
Write-Host ""
Write-Host "  Found $($files.Count) files ($(Format-Size $totalSize))"
Write-Host ""

if ($DryRun) {
    Write-Host "  Files to include:"
    $files | ForEach-Object {
        $rel = $_.FullName.Substring($RepoRoot.Length + 1)
        Write-Host "    $rel"
    }
    Write-Host ""
    Write-Host "  (dry run - no files copied)" -ForegroundColor Yellow
    exit 0
}

# Create output directory
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null

# Copy files
$copied = 0
foreach ($f in $files) {
    $rel = $f.FullName.Substring($RepoRoot.Length + 1)
    $dest = Join-Path $OutputDir $rel
    $destDir = Split-Path $dest -Parent
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    Copy-Item -Path $f.FullName -Destination $dest
    $copied++
}

# Generate manifest
$manifestFiles = $files | ForEach-Object { $_.FullName.Substring($RepoRoot.Length + 1) }
$manifest = @{
    release_name     = $OutputName
    created_at       = (Get-Date -Format "o")
    generated_by     = "make_release.ps1"
    release_mode     = $(if ($DryRun) { "dry_run" } else { "create" })
    included_files   = $manifestFiles
    total_file_count = $files.Count
    total_size_bytes = $totalSize
    warnings         = @()
    exclude_patterns = @{
        dirs       = $ExcludeDirs | Sort-Object
        extensions = $ExcludeExts | Sort-Object
        files      = $ExcludeFiles | Sort-Object
    }
}

$manifestPath = Join-Path $OutputDir "RELEASE_MANIFEST.json"
$manifest | ConvertTo-Json -Depth 3 | Out-File -FilePath $manifestPath -Encoding utf8

Write-Host "  Copied $copied/$($files.Count) files to $OutputDir"
Write-Host "  Manifest: $manifestPath"

# Create zip if requested
if ($Zip) {
    $zipPath = Join-Path (Split-Path $OutputDir -Parent) "$OutputName.zip"
    Write-Host "  Creating zip: $zipPath"
    Compress-Archive -Path ($files.FullName) -DestinationPath $zipPath -CompressionLevel Optimal
    $zipItem = Get-Item $zipPath
    Write-Host "  Zip created: $zipPath ($(Format-Size $zipItem.Length))"
}

Write-Host ""
Write-Host "Release package created successfully." -ForegroundColor Green