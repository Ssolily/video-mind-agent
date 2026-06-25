"""Check worker and queue status."""
import argparse
import json as j
import urllib.request

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    r = {"backend_healthy": False, "info": None, "error": None}
    try:
        req = urllib.request.Request(args.backend_url + "/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            r["backend_healthy"] = resp.status == 200
    except Exception as e:
        r["error"] = "Health: " + str(e)
    if r["backend_healthy"]:
        try:
            qpath = "/api/v1/q/info"
            req = urllib.request.Request(args.backend_url + qpath)
            with urllib.request.urlopen(req, timeout=5) as resp:
                r["info"] = j.loads(resp.read())
        except Exception as e:
            r["error"] = "Info: " + str(e)
    if args.json:
        print(j.dumps(r, ensure_ascii=False, indent=2))
        return
    print("=== Worker & Queue Status ===")
    print("  Backend:", r["backend_healthy"])
    qi = r.get("info")
    if qi:
        qs = qi.get("q_size", 0)
        mqs = qi.get("max_queue_size", 20)
        print(f"  Queue size:    {qs}/{mqs}")
        if mqs and qs >= mqs * 0.8:
            print("  [WARN] Queue near capacity!")
        at = qi.get("active_task")
        if at:
            print("  Active task:", at.get("task_id"), "(worker:", at.get("worker_id") + ")")
        else:
            print("  Active task:  none")
        print("  Workers:", qi.get("active_workers", 0), "/", qi.get("worker_concurrency", 1))
        sc = qi.get("status_counts", {})
        if sc:
            print("  Status counts:", j.dumps(sc))
        stale = qi.get("stale_running_tasks", [])
        if stale:
            print(f"  [WARN] Stale running tasks: {len(stale)}")
            for s in stale:
                print(f"    {s['task_id']} ({s['elapsed_sec']}s)")
        oc = qi.get("oldest_queued_task_age_sec")
        if oc is not None:
            print(f"  Oldest queued: {oc}s")
        tc = qi.get("timeout_config", {})
        if tc:
            print(f"  Timeouts: {j.dumps(tc)}")
    if r.get("error"):
        print("  Error:", r["error"])
    print("=" * 30)

if __name__ == "__main__":
    main()
