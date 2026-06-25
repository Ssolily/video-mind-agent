"""Background task monitor: periodic timeout checks, disk space, heartbeat."""
import logging
import threading
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_monitor_thread: threading.Thread | None = None
_stop_event = threading.Event()
_interval = 30


def start_monitor(interval_sec: int = 30) -> None:
    """Start the background monitor thread."""
    global _monitor_thread, _interval
    if _monitor_thread is not None and _monitor_thread.is_alive():
        logger.info("Monitor already running")
        return
    _interval = interval_sec
    _stop_event.clear()
    _monitor_thread = threading.Thread(target=_monitor_loop, daemon=True, name="task-monitor")
    _monitor_thread.start()
    logger.info("Task monitor started (interval=%ds)", interval_sec)


def stop_monitor(timeout: float = 5.0) -> None:
    """Stop the background monitor thread."""
    _stop_event.set()
    if _monitor_thread and _monitor_thread.is_alive():
        _monitor_thread.join(timeout=timeout)
    logger.info("Task monitor stopped")


def is_monitor_running() -> bool:
    return _monitor_thread is not None and _monitor_thread.is_alive()


def _monitor_loop() -> None:
    while not _stop_event.is_set():
        try:
            _run_checks()
        except Exception:
            logger.exception("Monitor: unexpected error in check cycle")
        _stop_event.wait(timeout=_interval)


def _run_checks() -> None:
    """Run all periodic checks."""
    from app.services import task_queue
    from app.config import TASK_TIMEOUT_SEC, STEP_TIMEOUT_SEC, TASK_STALE_SEC, MONITOR_INTERVAL_SEC

    # 1. Timeout check
    marked = task_queue.check_timeouts(
        config_timeout=TASK_TIMEOUT_SEC,
        step_timeout=STEP_TIMEOUT_SEC,
        stale_timeout=TASK_STALE_SEC,
    )
    if marked:
        logger.info("Monitor: timed out %d task(s): %s", len(marked), marked)

    # 2. Worker heartbeat update
    task_queue.update_heartbeat()

    # 3. Disk space check (log warning)
    _check_disk_space()


def _check_disk_space() -> None:
    """Check free disk space and log warning if low."""
    try:
        import shutil
        from app.config import DATA_DIR, MIN_FREE_DISK_GB
        usage = shutil.disk_usage(str(DATA_DIR))
        free_gb = usage.free / (1024**3)
        if free_gb < MIN_FREE_DISK_GB:
            logger.warning(
                "Low disk space: %.1f GB free (threshold: %d GB)",
                free_gb, MIN_FREE_DISK_GB,
            )
    except Exception:
        pass
