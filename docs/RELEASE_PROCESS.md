# Release Process

## Overview

This document describes the process for creating a VideoMind Agent release.

## Prerequisites

- All tests pass
- typecheck passes
- Build succeeds
- Privacy check passes
- Docker compose config validates

## Release Package Contents

The release package includes:
- `backend/` — FastAPI backend source code
- `frontend/` — React + Vite frontend source code
- `scripts/` — Utility scripts (not runtime logs)
- `docs/` — Documentation
- `Dockerfile`, `docker-compose.yml`, `.dockerignore` — Docker deployment
- `.env.example`, `.env.docker.example` — Configuration templates
- `README.md`, `AGENTS.md`, `RELEASE_NOTES_TEMPLATE.md`

The release package **excludes**:
- `backend/svr.log`, `backend/svr2.log`, and all `*.log` files
- `PROJECT_AUDIT.md` — internal audit document
- All `P*_REPORT.md` and `P*_DRAFT.md` history reports
- `data/`, `logs/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`
- Model weights, video files, zip archives
- `.env` files with real credentials
- `dist/` old release packages

## Step-by-Step Release Process

### 1. Run Full Test Suite

```powershell
# Backend
cd backend
pytest -ra -q

# Frontend
cd frontend
npm run typecheck
npm run test:run
npm run build
```

### 2. Run Regression Check

```powershell
.\scripts\check_all.ps1
```

### 3. Run Privacy Check

```powershell
# Default mode (errors only — release gate)
python scripts/check_privacy.py

# Strict mode (includes all warnings)
python scripts/check_privacy.py --strict

# JSON output for automation
python scripts/check_privacy.py --json
```

**Important:** The release gate requires **0 errors** in default mode. If the check
fails, fix the issues before proceeding:

- API Key found in source → Redact immediately and revoke the key
- Windows absolute path (e.g. `C:\Users\...`) → Replace with `<USERPROFILE>` or `<PROJECT_ROOT>`
- `.env` content leaked → Remove from tracked files

### 3a. Privacy-Gated Release Dry-Run

```powershell
# This will fail if privacy check finds errors
python scripts/make_release.py --dry-run --check-privacy
```

### 4. Validate Docker Config

```powershell
cp .env.docker.example .env.docker
docker compose config
```

### 5. Create Release Package

```powershell
# Preview what will be included (with privacy gate)
python scripts/make_release.py --dry-run --check-privacy

# Create release directory (privacy check runs automatically)
python scripts/make_release.py

# Create zip archive
python scripts/make_release.py --zip

# Custom output directory
python scripts/make_release.py --output ./my-release

# ⚠️ Skip privacy check (not recommended for release builds)
python scripts/make_release.py --skip-privacy-check
```

### 6. Verify Release Package (After --zip)

```powershell
# Check manifest
cat dist/video-mind-agent-release-*/RELEASE_MANIFEST.json

# Run privacy check on extracted release
Expand-Archive dist/video-mind-agent-release-*.zip dist/release_verify -Force
cd dist/release_verify/video-mind-agent-release-*
python scripts/check_privacy.py

# Verify release zip checksum
Get-Content dist/SHA256SUMS.txt
# Compare: certutil -hashfile dist/video-mind-agent-release-*.zip SHA256

# Verify backend starts (if Docker available)
cd dist/video-mind-agent-release-*
cp .env.docker.example .env.docker
docker compose up -d --build
curl http://127.0.0.1:8000/health
docker compose down

# Run smoke tests in extracted release
cd backend && pytest -ra -q && cd ..
cd frontend && npm run typecheck && npm run test:run && npm run build && cd ..
```

### 7. Update Documentation

- Update README.md version references if applicable
- Update RELEASE_NOTES_TEMPLATE.md with actual release notes

### 8. Tag Release (Git)

```bash
git tag -a v1.0.0 -m "Version 1.0.0"
git push origin v1.0.0
```

## Version Numbering

Suggest following [Semantic Versioning](https://semver.org/):

- **Major** (1.x.x): Breaking changes to API or storage format
- **Minor** (x.1.x): New features, backward compatible
- **Patch** (x.x.1): Bug fixes, performance improvements

Current suggested version: `1.0.0-alpha`

## Release Artifacts

| Artifact | Location |
|----------|----------|
| Source package | `dist/video-mind-agent-release-YYYYMMDD-HHMMSS/` |
| Zip archive | `dist/video-mind-agent-release-YYYYMMDD-HHMMSS.zip` |
| Release manifest | `RELEASE_MANIFEST.json` |
| Docker image | Built locally via `docker compose build` |

## Rollback

If a release introduces issues:

1. Revert to previous release package
2. Restore data backup (if applicable)
3. Run full test suite before re-deploying

## Known Limitations (Template)

- Docker version uses in-process queue (no Redis/Celery)
- CPU mode recommended for Docker (GPU requires manual setup)
- Frontend runs locally (not included in Docker container)
- SQLite database (not suitable for multi-process deployment)
