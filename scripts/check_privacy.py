#!/usr/bin/env python3
"""Lightweight privacy scanner for VideoMind Agent source tree.
Scans for API keys, Windows absolute paths, and other sensitive content.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

SKIP_DIRS = {
    ".git", "data", "logs", "node_modules", "__pycache__",
    ".pytest_cache", ".pytest_tmp", "test_tmp",
    "dist", "frontend/dist", "frontend/node_modules",
    ".mypy_cache", ".ruff_cache", ".idea", ".vscode",
    "venv", ".venv", "env", ".env",
    "models", "sam2", "tools",
}

SCAN_EXTS = {".py", ".js", ".ts", ".tsx", ".jsx", ".md", ".yml", ".yaml",
             ".toml", ".cfg", ".ini", ".env", ".sh", ".ps1", ".json",
             ".txt", ".example", ".dockerignore", ".gitignore"}

SKIP_FILES = {".env", ".env.docker", ".env.docker.example",
              ".gitkeep", ".DS_Store", "Thumbs.db",
              "package-lock.json", "PROJECT_AUDIT.md"}

PATTERNS = [
    ("API_KEY_OPENAI", re.compile(r"sk-[A-Za-z0-9]{20,}"), "error"),
    ("API_KEY_DEEPSEEK", re.compile(r"(?:DEEPSEEK|deepseek)_API_KEY\s*=\s*['""]?(?!sk-your|<your_|<REDACTED_)[A-Za-z0-9_-]{10,}"), "error"),
    ("API_KEY_GENERIC", re.compile(r"(?:api_key|API_KEY|apikey)\s*[:=]\s*['""]?[A-Za-z0-9_-]{20,}"), "error"),
    ("WIN_ABS_PATH", re.compile(r"[A-Za-z]:\\(?:Users|home|tmp|temp|projects|code)"), "error"),
    ("ENV_FILE_CONTENT", re.compile(r"^DEEPSEEK_API_KEY=", re.MULTILINE), "error"),
]

ALLOWLIST = [
    re.compile(r"DEEPSEEK_API_KEY=[ \t]*$"),
    re.compile(r"DEEPSEEK_API_KEY=[ \t]*['""]?[ \t]*['""]?$"),
    re.compile(r"sk-[A-Za-z0-9]{7}\."),
    re.compile(r"yolo11n\.pt"),
    re.compile(r"<REDACTED_[A-Z_]+>"),
    re.compile(r"<USERPROFILE>"),
    re.compile(r"sk-your-key-here"),
    re.compile(r"e\.g\.\s*\`[A-Za-z]:\\\\"),
    re.compile(r"C:\\\\Users\\\\\.\.\.\s*\)"),
]

def _should_skip(path):
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    if path.name in SKIP_FILES:
        return True
    if path.suffix.lower() not in SCAN_EXTS:
        return True
    return False

def _is_allowlisted(line):
    for pattern in ALLOWLIST:
        if pattern.search(line):
            return True
    return False

def scan_file(filepath, strict=False):
    issues = []
    try:
        text = filepath.read_bytes()
        if b"\x00" in text[:1024]:
            return issues
        text = text.decode("utf-8", errors="replace")
    except (OSError, PermissionError):
        return issues
    for lineno, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _is_allowlisted(stripped):
            continue
        for name, pattern, severity in PATTERNS:
            if not strict and severity == "warning":
                continue
            m = pattern.search(stripped)
            if m:
                match_text = m.group()
                snippet = match_text[:12] + "..." if len(match_text) > 16 else match_text
                issues.append({
                    "path": str(filepath),
                    "line": lineno,
                    "type": name,
                    "severity": severity,
                    "snippet": snippet,
                })
                break
    return issues

def scan_root(root, strict=False):
    all_issues = []
    scanned = 0
    for entry in sorted(root.rglob("*")):
        if _should_skip(entry):
            continue
        if not entry.is_file():
            continue
        scanned += 1
        issues = scan_file(entry, strict=strict)
        all_issues.extend(issues)
    return all_issues, scanned

def format_results(issues, scanned):
    lines = [f"Scanned {scanned} files"]
    if not issues:
        lines.append("No privacy issues found.")
        return "\n".join(lines)
    errors = [i for i in issues if i["severity"] == "error"]
    warnings = [i for i in issues if i["severity"] == "warning"]
    lines.append(f"Found {len(issues)} issue(s) ({len(errors)} errors, {len(warnings)} warnings)")
    lines.append("")
    for sev in ("error", "warning"):
        for item in [i for i in issues if i["severity"] == sev]:
            lines.append(f"  [{sev.upper()}] {item['path']}:{item['line']}  {item['type']}")
            lines.append(f"          snippet: {item['snippet']}")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Scan repo for privacy issues")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--strict", action="store_true", help="Include warnings")
    parser.add_argument("--path", default=".", help="Path to scan")
    args = parser.parse_args()
    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        sys.exit(1)
    issues, scanned = scan_root(root, strict=args.strict)
    if args.json:
        print(json.dumps({
            "scanned": scanned,
            "total_issues": len(issues),
            "errors": len([i for i in issues if i["severity"] == "error"]),
            "warnings": len([i for i in issues if i["severity"] == "warning"]),
            "issues": issues,
        }, ensure_ascii=False, indent=2))
    else:
        print(format_results(issues, scanned))
    error_count = len([i for i in issues if i["severity"] == "error"])
    sys.exit(1 if error_count > 0 else 0)

if __name__ == "__main__":
    main()