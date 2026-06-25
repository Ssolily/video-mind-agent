"""Verify MVP delivery readiness by checking backend, frontend, and result API.

Usage
-----
    conda activate agent
    python scripts/verify_mvp_delivery.py [--backend-url URL] [--video-id ID]
                                         [--frontend-url URL] [--output FILE]

Examples
--------
    # Quick check against running services (no video)
    python scripts/verify_mvp_delivery.py

    # Full check with a known video_id
    python scripts/verify_mvp_delivery.py --video-id abc123

    # Output JSON report
    python scripts/verify_mvp_delivery.py --video-id abc123 --output docs/demo/delivery_report.json
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPORT_TEMPLATE = {
    "backend_healthy": False,
    "frontend_reachable": False,
    "video_id": None,
    "result_api": {},
    "source_accessible": False,
    "clip_accessible": False,
    "highlight_validation": {},
    "windows_path_leak": [],
    "ffprobe_clip_valid": False,
    "passed": False,
    "errors": [],
    "warnings": [],
}


def check_url(url: str, timeout: float = 5.0) -> tuple[int, bytes | None, str | None]:
    """GET a URL and return (status, body, error)."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), None
    except urllib.error.HTTPError as e:
        return e.code, e.read(), None
    except Exception as e:
        return 0, None, str(e)


def check_health(backend_url: str) -> bool:
    """Check /health endpoint."""
    status, body, err = check_url(f"{backend_url}/health")
    if status == 200:
        return True
    return False


def check_frontend(frontend_url: str) -> bool:
    """Check frontend is reachable."""
    status, body, err = check_url(frontend_url)
    return status == 200


def has_windows_abs_path(obj, path="") -> list[str]:
    """Recursively check for Windows absolute paths in a JSON-like object."""
    issues = []
    if isinstance(obj, str):
        if obj.startswith(("C:\\", "D:\\", "C:/", "D:/")):
            issues.append(f"{path}: {obj[:80]}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            issues.extend(has_windows_abs_path(v, f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            issues.extend(has_windows_abs_path(v, f"{path}[{i}]"))
    return issues


def check_result_api(backend_url: str, video_id: str) -> dict:
    """Fetch and validate GET /api/v1/videos/{video_id}/result."""
    result = {
        "status_code": None,
        "valid": False,
        "has_video_id": False,
        "has_status": False,
        "has_duration": False,
        "has_source_url": False,
        "has_highlights": False,
        "has_clips": False,
        "has_report": False,
        "windows_path_leaks": [],
        "highlight_count": 0,
        "clip_count": 0,
        "body_preview": None,
        "error": None,
    }
    status, body, err = check_url(f"{backend_url}/api/v1/videos/{video_id}/result")
    result["status_code"] = status
    if err:
        result["error"] = err
        return result
    if not body:
        result["error"] = "Empty response body"
        return result
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        result["error"] = f"JSON decode error: {e}"
        return result
    result["has_video_id"] = "video_id" in data
    result["has_status"] = "status" in data
    result["has_duration"] = "duration" in data
    result["has_source_url"] = "source_url" in data
    result["has_highlights"] = "highlights" in data
    result["has_clips"] = "clips" in data
    result["has_report"] = "report" in data
    result["highlight_count"] = len(data.get("highlights", []))
    result["clip_count"] = len(data.get("clips", []))
    result["windows_path_leaks"] = has_windows_abs_path(data)
    result["body_preview"] = json.dumps(data, ensure_ascii=False)[:200]
    result["valid"] = (
        result["has_video_id"]
        and result["has_status"]
        and result["has_source_url"]
        and result["has_highlights"]
        and result["has_clips"]
    )
    return result


def check_highlight_validation(data: dict) -> dict:
    """Validate highlight fields."""
    validation = {
        "valid": True,
        "highlight_count": 0,
        "issues": [],
    }
    highlights = data.get("highlights", [])
    validation["highlight_count"] = len(highlights)
    for i, h in enumerate(highlights):
        msgs = []
        if not h.get("id"):
            msgs.append("missing id")
        if "start_time" not in h or h["start_time"] is None:
            msgs.append("missing start_time")
        if "end_time" not in h or h["end_time"] is None:
            msgs.append("missing end_time")
        if "duration" not in h or h["duration"] is None:
            msgs.append("missing duration")
        if msgs:
            validation["issues"].append(f"highlight[{i}]: " + ", ".join(msgs))
            validation["valid"] = False
    return validation


def resolve_url(url_str: str | None, backend_url: str) -> str | None:
    """Resolve a relative API URL to an absolute URL."""
    if not url_str:
        return None
    if url_str.startswith("/"):
        return f"{backend_url.rstrip('/')}{url_str}"
    if url_str.startswith("http"):
        return url_str
    return f"{backend_url.rstrip('/')}/{url_str.lstrip('/')}"


def check_source_accessible(backend_url: str, video_id: str) -> dict:
    """Check GET /api/v1/videos/{video_id}/source responds with 200."""
    status, body, err = check_url(f"{backend_url}/api/v1/videos/{video_id}/source")
    return {"status_code": status, "error": err, "range_support": status == 206 or status in (200, 206)}


def check_clip_accessible(backend_url: str, video_id: str, clip_url: str) -> dict:
    """Check a clip URL responds with 200."""
    url = resolve_url(clip_url, backend_url)
    if not url:
        return {"status_code": None, "error": "No clip URL available"}
    status, body, err = check_url(url)
    return {"status_code": status, "error": err}


def ffprobe_check(file_path: str) -> dict:
    """Use ffprobe to verify a clip file has video stream and duration."""
    result = {"valid": False, "duration": None, "has_video": False, "error": None}
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", file_path],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            result["error"] = proc.stderr[:200]
            return result
        data = json.loads(proc.stdout)
        streams = data.get("streams", [])
        result["has_video"] = any(s.get("codec_type") == "video" for s in streams)
        fmt = data.get("format", {})
        dur = fmt.get("duration")
        if dur:
            result["duration"] = float(dur)
        result["valid"] = result["has_video"] and (result["duration"] or 0) > 0
    except FileNotFoundError:
        result["error"] = "ffprobe not found"
    except Exception as e:
        result["error"] = str(e)
    return result


def main():
    parser = argparse.ArgumentParser(description="Verify MVP delivery readiness")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000", help="Backend URL")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173", help="Frontend URL")
    parser.add_argument("--video-id", default=None, help="Video ID to verify")
    parser.add_argument("--output", default=None, help="Output JSON report path")
    args = parser.parse_args()

    report = dict(REPORT_TEMPLATE)
    report["backend_url"] = args.backend_url
    report["frontend_url"] = args.frontend_url
    report["video_id"] = args.video_id

    # 1. Backend health
    backend_healthy = check_health(args.backend_url)
    report["backend_healthy"] = backend_healthy
    if not backend_healthy:
        report["errors"].append(f"Backend not healthy at {args.backend_url}/health")

    # 2. Frontend reachable
    frontend_ok = check_frontend(args.frontend_url)
    report["frontend_reachable"] = frontend_ok
    if not frontend_ok:
        report["errors"].append(f"Frontend not reachable at {args.frontend_url}")

    # 3-9. Video-specific checks
    if args.video_id:
        # 3. Result API
        result_info = check_result_api(args.backend_url, args.video_id)
        report["result_api"] = result_info
        if result_info["windows_path_leaks"]:
            report["windows_path_leak"].extend(result_info["windows_path_leaks"])

        if result_info["valid"] and result_info.get("body_preview"):
            data_sample = json.loads(result_info["body_preview"])
        else:
            data_sample = {}

        # 4. Source accessible
        source_info = check_source_accessible(args.backend_url, args.video_id)
        report["source_accessible"] = source_info.get("status_code") == 200
        report["source_status_code"] = source_info["status_code"]

        # 5. Highlight validation
        if result_info.get("body_preview"):
            full_data = json.loads(
                urllib.request.urlopen(
                    f"{args.backend_url}/api/v1/videos/{args.video_id}/result", timeout=5
                ).read()
            )
            try:
                req = urllib.request.Request(f"{args.backend_url}/api/v1/videos/{args.video_id}/result")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    full_data = json.loads(resp.read())
                report["highlight_validation"] = check_highlight_validation(full_data)
            except Exception as e:
                report["highlight_validation"]["issues"].append(str(e))

        # 6. Clip accessible
        if result_info.get("body_preview"):
            try:
                req = urllib.request.Request(f"{args.backend_url}/api/v1/videos/{args.video_id}/result")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    full_data = json.loads(resp.read())
                for clip in full_data.get("clips", []):
                    clip_url = clip.get("url", "")
                    clip_result = check_clip_accessible(args.backend_url, args.video_id, clip_url)
                    if clip_result.get("status_code") == 200:
                        report["clip_accessible"] = True
                        break
            except Exception as e:
                report["clip_accessible"] = False

    # 7. ffprobe check (if clip files locally accessible)
    clip_dir = Path("data/clips")
    if clip_dir.exists():
        clip_files = list(clip_dir.rglob("*.mp4"))
        if clip_files:
            probe = ffprobe_check(str(clip_files[0]))
            report["ffprobe_clip_valid"] = probe["valid"]
            if not probe["valid"] and probe.get("error"):
                report["errors"].append(f"ffprobe check failed: {probe['error']}")

    # 8. Overall pass/fail
    passed = (
        report["backend_healthy"]
        and report["frontend_reachable"]
    )
    if args.video_id:
        passed = passed and report["result_api"].get("valid", False)
    report["passed"] = passed

    # Output
    output_text = json.dumps(report, ensure_ascii=False, indent=2)
    print("=" * 60)
    print("  MVP DELIVERY VERIFICATION REPORT")
    print("=" * 60)
    print(f"  Backend healthy:      {'[OK]' if report['backend_healthy'] else '[FAIL]'} {args.backend_url}")
    print(f"  Frontend reachable:   {'[OK]' if report['frontend_reachable'] else '[FAIL]'} {args.frontend_url}")
    if args.video_id:
        print(f"  Video ID:             {args.video_id}")
        r = report["result_api"]
        print(f"  Result API status:    {r.get('status_code')} {'[OK]' if r.get('valid') else '[FAIL]'}")
        print(f"  Highlights:           {r.get('highlight_count', '?')}")
        print(f"  Clips:                {r.get('clip_count', '?')}")
        print(f"  Source accessible:    {'[OK]' if report['source_accessible'] else '[FAIL]'}")
        print(f"  Clip accessible:      {'[OK]' if report['clip_accessible'] else '[FAIL]'}")
    if report["windows_path_leak"]:
        print(f"  [!]️  Windows path leaks: {len(report['windows_path_leak'])}")
    if report["errors"]:
        print(f"  Errors:               {len(report['errors'])}")
        for e in report["errors"]:
            print(f"    - {e}")
    print(f"\n  Overall:              {'[OK] PASSED' if passed else '[FAIL] FAILED'}")
    print("=" * 60)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output_text, encoding="utf-8")
        print(f"\n  Report saved to: {out_path.resolve()}")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
