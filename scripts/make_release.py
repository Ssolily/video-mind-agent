#!/usr/bin/env python3
"""Create a release package for VideoMind Agent.

Usage:
    python scripts/make_release.py --dry-run
    python scripts/make_release.py --zip
    python scripts/make_release.py --output ./my-release
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

INCLUDE_PATHS = [
    "backend",
    "scripts",
    "docs",
    "Dockerfile",
    "docker-compose.yml",
    ".dockerignore",
    ".env.example",
    ".env.docker.example",
    "README.md",
    "frontend",
    "AGENTS.md",
]

EXCLUDE_DIRS = {
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "node_modules", ".git", "data", "logs",
    "test_tmp", ".pytest_tmp", "venv", ".venv", "env", ".env",
    "dist", "frontend/dist",
    "models", "sam2", "tools",
    "__pycache__",
}

EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".pt", ".pth", ".bin", ".onnx",
                      ".log",
                      ".log",
                      ".mp4", ".mov", ".avi", ".mkv", ".webm",
                      ".zip", ".tar.gz", ".tgz", ".wav", ".mp3"}

EXCLUDE_FILES = {".env", ".DS_Store", "Thumbs.db", "yolo11n.pt", "PROJECT_AUDIT.md",
                 "package-lock.json"}


def _match_exclude_name(name: str) -> bool:
    """Check if a file name matches an exclusion pattern."""
    import re
    patterns = [
        re.compile(r"^P\d.*_REPORT\.md$"),
        re.compile(r"^P\d.*_DRAFT\.md$"),
        re.compile(r"^HIGHLIGHT_REFACTOR_REPORT\.md$"),
        re.compile(r"^ROADMAP_.*\.md$"),
    ]
    for pat in patterns:
        if pat.match(name):
            return True
    return False


def _should_exclude(path: Path, base: Path) -> bool:
    """Check if a path should be excluded from the release."""
    try:
        rel = path.relative_to(base)
    except ValueError:
        return True
    for part in rel.parts:
        if part in EXCLUDE_DIRS:
            return True
    if path.name in EXCLUDE_FILES:
        return True
    if path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True
    if _match_exclude_name(path.name):
        return True
    return False


def _collect_files(base: Path, paths: list[str]) -> list[Path]:
    """Collect all files from the given paths under base."""
    files = []
    for p in paths:
        full = (base / p).resolve()
        if not full.exists():
            print(f"  [WARN] {p} does not exist, skipping")
            continue
        if full.is_file():
            if not _should_exclude(full, base):
                files.append(full)
        elif full.is_dir():
            for f in sorted(full.rglob("*")):
                if f.is_file() and not _should_exclude(f, base):
                    files.append(f)
    return files


def _format_size(b: int) -> str:
    if b > 1024**3:
        return f"{b/(1024**3):.2f} GB"
    elif b > 1024**2:
        return f"{b/(1024**2):.2f} MB"
    elif b > 1024:
        return f"{b/1024:.1f} KB"
    return f"{b} B"


def main():
    parser = argparse.ArgumentParser(description="Create VideoMind Agent release package")
    parser.add_argument("--dry-run", action="store_true", help="Preview without copying")
    parser.add_argument("--zip", action="store_true", help="Create zip archive")
    parser.add_argument("--output", default=None, help="Output directory (default: dist/)")
    parser.add_argument("--check-privacy", action="store_true", help="Run privacy check before packaging; fail if issues found")
    parser.add_argument("--skip-privacy-check", action="store_true", help="Skip privacy check (not recommended)")
    args = parser.parse_args()

    now = datetime.now()
    ts = now.strftime("%Y%m%d-%H%M%S")
    output_name = f"video-mind-agent-release-{ts}"
    output_root = Path(args.output or (REPO_ROOT / "dist"))
    output_dir = output_root / output_name

    print(f"=== VideoMind Agent Release Packaging ===")
    print(f"  Source: {REPO_ROOT}")
    print(f"  Output: {output_dir}")
    print(f"  Mode:   {'DRY RUN' if args.dry_run else 'CREATE'}")
    print()

    privacy_check_status = "skipped"
    # Privacy check gate
    if args.check_privacy or (not args.skip_privacy_check and not args.dry_run):
        print("  Running privacy check...")
        import subprocess
        privacy_result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "check_privacy.py"), "--json"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        privacy_check_status = "passed"
        if privacy_result.returncode != 0:
            print(privacy_result.stdout)
            print("  [ERROR] Privacy check failed. Release packaging blocked.")
            print("  To override: --skip-privacy-check (not recommended)")
            sys.exit(1)
        else:
            import json as _json
            try:
                privacy_data = _json.loads(privacy_result.stdout)
                print(f"  Privacy check: {privacy_data.get('scanned', 0)} files, {privacy_data.get('total_issues', 0)} issues")
            except Exception:
                print("  Privacy check: passed")
        print()

    print()

    # Collect files
    files = _collect_files(REPO_ROOT, INCLUDE_PATHS)
    total_size = sum(f.stat().st_size for f in files)

    print(f"  Found {len(files)} files ({_format_size(total_size)})")
    print()

    if args.dry_run:
        print("  Files to include:")
        for f in files:
            try:
                rel = f.relative_to(REPO_ROOT)
                print(f"    {rel}")
            except ValueError:
                print(f"    {f.name}")
        print()
        print("  (dry run - no files copied)")
        return

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Copy files
    copied = 0
    for f in files:
        try:
            rel = f.relative_to(REPO_ROOT)
            dest = output_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            copied += 1
        except Exception as e:
            print(f"  [ERROR] {f}: {e}")

    # Generate manifest
    # Check for excluded sensitive files
    excluded_sensitive = [f for f in EXCLUDE_FILES if (REPO_ROOT / f).exists() and f not in {"package-lock.json"}]
    warnings_list = []
    for f in excluded_sensitive:
        warnings_list.append(f"Excluded sensitive file: {f}")
    # Count P*_REPORT.md files in root
    p_report_count = len(list(REPO_ROOT.glob("P*_REPORT.md")))
    if p_report_count > 0:
        warnings_list.append(f"Excluded {p_report_count} P*_REPORT.md history files from root")

    manifest = {
        "release_name": output_name,
        "created_at": now.isoformat(),
        "generated_by": "make_release.py",
        "release_mode": "dry_run" if args.dry_run else "create",
        "generated_by": "make_release.py",
        "release_mode": "dry_run" if args.dry_run else "create",
        "included_files": [str(f.relative_to(REPO_ROOT)) for f in files],
        "total_file_count": len(files),
        "total_size_bytes": total_size,
        "privacy_check_result": privacy_check_status,
        "warnings": warnings_list,
        "exclude_patterns": {
            "dirs": sorted(EXCLUDE_DIRS),
            "extensions": sorted(EXCLUDE_EXTENSIONS),
            "files": sorted(EXCLUDE_FILES),
        },
    }
    manifest_path = output_dir / "RELEASE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  Copied {copied}/{len(files)} files to {output_dir}")
    print(f"  Manifest: {manifest_path}")

    # Create zip if requested
    if args.zip:
        import zipfile
        zip_path = output_root / f"{output_name}.zip"
        print(f"  Creating zip: {zip_path}")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                try:
                    rel = f.relative_to(REPO_ROOT)
                    zf.write(f, rel)
                except ValueError:
                    pass
            if manifest_path.exists():
                zf.write(manifest_path, "RELEASE_MANIFEST.json")
        print(f"  Zip created: {zip_path} ({_format_size(zip_path.stat().st_size)})")

    print()
    print("Release package created successfully.")


if __name__ == "__main__":
    main()