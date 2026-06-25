"""Check storage health."""
import argparse
import json as j
import shutil
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Check storage health")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--local", action="store_true", help="Check local data dir directly")
    args = parser.parse_args()

    if args.local:
        data_dir = Path(__file__).resolve().parent.parent / "data"
        if not data_dir.is_dir():
            print("Data dir not found:", data_dir)
            return
        usage = shutil.disk_usage(str(data_dir))
        free_gb = round(usage.free / (1024**3), 2)
        print("=== Local Storage Health ===")
        print("  Data dir:", data_dir)
        print("  Free:", free_gb, "GB")
        print("  Used:", round(usage.used / (1024**3), 2), "GB")
        for sub in ["raw_videos", "clips", "reports", "task_logs"]:
            d = data_dir / sub
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) / (1024**3) if d.is_dir() else 0
            print(f"  {sub}: {round(size, 4)} GB")
        return

    r = {"healthy": False, "info": None, "error": None}
    try:
        req = urllib.request.Request(args.backend_url + "/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            r["healthy"] = resp.status == 200
    except Exception as e:
        r["error"] = "Health: " + str(e)

    if r["healthy"]:
        try:
            req = urllib.request.Request(args.backend_url + "/api/v1/system/storage")
            with urllib.request.urlopen(req, timeout=5) as resp:
                r["info"] = j.loads(resp.read())
        except Exception as e:
            r["error"] = "Storage: " + str(e)

    if args.json:
        print(j.dumps(r, ensure_ascii=False, indent=2))
        return

    print("=== Storage Health ===")
    print("  Backend:", r["healthy"])
    info = r.get("info")
    if info:
        print(f"  Free: {info.get('free_gb', '?')} GB (min: {info.get('min_free_disk_gb', '?')} GB)")
        print(f"  Used: {info.get('used_gb', '?')} GB")
        for k in ["uploads_gb", "clips_gb", "reports_gb", "task_logs_gb"]:
            v = info.get(k)
            if v is not None:
                print(f"  {k}: {v} GB")
        w = info.get("warnings", [])
        if w:
            print("  Warnings:")
            for ww in w:
                print(f"    - {ww}")
    if r.get("error"):
        print("  Error:", r["error"])


if __name__ == "__main__":
    main()
