"""Check highlight evaluation experiment files for privacy/security issues.

Scans JSON, Markdown, CSV, and text files under a given root directory
for local absolute paths, sensitive keywords, email addresses, and
large binary files that should not be committed.

Usage:
    python scripts/check_experiment_privacy.py --root experiments/highlight_eval/real_dataset
"""

import argparse, re, sys
from pathlib import Path


# ── Pattern definitions ──────────────────────────────

# Windows absolute path: C:\\, D:\\, etc.
RE_WIN_ABS = re.compile(r"[A-Za-z]:\\")

# Unix absolute paths
RE_UNIX_ABS = re.compile(r'/(?:home|Users|mnt|tmp|var|opt|usr)/[A-Za-z0-9_]')

# Sensitive keywords
RE_SENSITIVE = re.compile(
    r"(?:"
    r"API_KEY|api_key|APIKEY|SECRET|secret|TOKEN|token|PASSWORD|password"
    r"|PRIVATE_KEY|private_key"
    r")",
    re.IGNORECASE,
)

# Email (simple pattern)
RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Video file extensions
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv"}

# Ignored directories
IGNORED_DIRS = {
    "__pycache__", ".pytest_cache", ".git", ".venv", "venv",
    "node_modules", ".vscode", ".idea", "dist", "build",
}

# Files to skip
SKIP_FILES = {".gitkeep", ".DS_Store", "Thumbs.db"}

# Extensions to scan
TEXT_EXTS = {".json", ".md", ".csv", ".txt", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".env"}


def scan_file(filepath: Path, verbose: bool = False) -> list[dict]:
    """Scan a single text file for privacy issues.

    Returns list of dicts with keys: path, line, type, snippet.
    """
    issues = []
    if filepath.name in SKIP_FILES or filepath.suffix.lower() not in TEXT_EXTS:
        return issues

    try:
        raw = filepath.read_bytes()
        # Skip binary files
        if b"\x00" in raw[:1024]:
            if verbose:
                print(f"  SKIP (binary): {filepath}")
            return issues
        text = raw.decode("utf-8")
    except (UnicodeDecodeError, PermissionError, OSError) as e:
        if verbose:
            print(f"  SKIP ({e}): {filepath}")
        return issues

    lines = text.split("\n")
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        snippet = stripped[:80].strip()

        # Windows absolute path
        if RE_WIN_ABS.search(stripped):
            issues.append({
                "path": str(filepath),
                "line": lineno,
                "type": "WIN_ABS_PATH",
                "severity": "error",
                "snippet": snippet,
            })

        # Unix absolute path  
        if RE_UNIX_ABS.search(stripped):
            issues.append({
                "path": str(filepath),
                "line": lineno,
                "type": "UNIX_ABS_PATH",
                "severity": "error",
                "snippet": snippet,
            })

        # Sensitive keywords
        for m in RE_SENSITIVE.finditer(stripped):
            kw = m.group()
            # Skip false positives (e.g. the word "token" in description contexts)
            # Only flag if it looks like a value assignment or env-style usage
            if "=" in stripped and kw.upper() in stripped.upper():
                issues.append({
                    "path": str(filepath),
                    "line": lineno,
                    "type": "SENSITIVE_KEYWORD",
                    "severity": "error",
                    "snippet": snippet,
                })

        # Email
        for m in RE_EMAIL.finditer(stripped):
            email = m.group()
            # Filter test / example emails
            if email.endswith((".example.com", ".test", "@example.com")):
                continue
            issues.append({
                "path": str(filepath),
                "line": lineno,
                "type": "EMAIL",
                "severity": "warning",
                "snippet": snippet,
            })

    return issues


def scan_root(root: Path, include_exts: set | None = None,
              verbose: bool = False) -> list[dict]:
    """Recursively scan all text files under root.

    Returns list of all found issues.
    """
    if include_exts is None:
        include_exts = TEXT_EXTS

    all_issues = []
    scanned = 0
    video_files = []

    for entry in sorted(root.rglob("*")):
        # Skip ignored dirs
        if any(part in IGNORED_DIRS for part in entry.parts):
            continue
        if not entry.is_file():
            continue

        # Check for video files (warning only)
        if entry.suffix.lower() in VIDEO_EXTS:
            video_files.append(entry)
            all_issues.append({
                "path": str(entry),
                "line": 1,
                "type": "VIDEO_FILE",
                "severity": "warning",
                "snippet": entry.name[:80],
            })

        # Scan text files
        if entry.suffix.lower() in include_exts:
            scanned += 1
            if verbose:
                print(f"  Scanning: {entry.relative_to(root)}")
            issues = scan_file(entry, verbose)
            all_issues.extend(issues)

    if verbose:
        print(f"\n  Scanned {scanned} text files, {len(video_files)} video files")

    return all_issues


def format_issues(issues: list[dict]) -> str:
    """Format issues as a human-readable report."""
    if not issues:
        return "Privacy check passed: no issues found"

    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    lines = [f"Privacy check failed: {len(errors)} error(s), {len(warnings)} warning(s)"]
    for issue_list, label in [(errors, "ERROR"), (warnings, "WARNING")]:
        if not issue_list:
            continue
        lines.append(f"\n{label}S:")
        for iss in issue_list:
            lines.append(f"  [{iss['type']}] {iss['path']}:{iss['line']}")
            lines.append(f"    {iss['snippet']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Check experiment files for privacy/security issues."
    )
    parser.add_argument("--root", required=True,
                        help="Root directory to scan")
    parser.add_argument("--include-json", action="store_true",
                        help="Include .json files (default: included)")
    parser.add_argument("--include-md", action="store_true",
                        help="Include .md files (default: included)")
    parser.add_argument("--include-csv", action="store_true",
                        help="Include .csv files (default: included)")
    parser.add_argument("--fail-on-warning", action="store_true",
                        help="Exit with non-zero code on warnings too")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose output")

    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"ERROR: {args.root} is not a directory")
        sys.exit(1)

    # Determine extensions to scan
    exts = set(TEXT_EXTS)
    if args.include_json:
        exts.add(".json")
    if args.include_md:
        exts.add(".md")
    if args.include_csv:
        exts.add(".csv")

    issues = scan_root(root, exts, args.verbose)

    result = format_issues(issues)
    print(result)

    errors = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]

    has_error = len(errors) > 0
    has_warning = len(warnings) > 0 and args.fail_on_warning

    if has_error or has_warning:
        sys.exit(1)


if __name__ == "__main__":
    main()
