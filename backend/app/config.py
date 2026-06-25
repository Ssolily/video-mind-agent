import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent

# --- Directories -----------------------------------------------------------

DATA_DIR = Path(os.getenv(
    "VIDEOMIND_DATA_DIR", str(BASE_DIR / "data"),
))
MODEL_DIR = Path(os.getenv(
    "VIDEOMIND_MODEL_DIR", str(BASE_DIR),
))
RAW_VIDEOS_DIR = DATA_DIR / "raw_videos"
FRAMES_DIR = DATA_DIR / "frames"
REPORTS_DIR = DATA_DIR / "reports"
AUDIO_DIR = DATA_DIR / "audio"
CLIPS_DIR = DATA_DIR / "clips"

for _dir in [RAW_VIDEOS_DIR, FRAMES_DIR, REPORTS_DIR, AUDIO_DIR, CLIPS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# --- Model paths -----------------------------------------------------------

YOLO_MODEL_PATH = os.getenv(
    "VIDEOMIND_YOLO_MODEL_PATH", "yolo11n.pt",
)


# --- Upload limits ---------------------------------------------------------

MAX_UPLOAD_MB = int(os.getenv("VIDEOMIND_MAX_UPLOAD_MB", "500"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

MAX_VIDEO_DURATION_SEC = float(os.getenv("VIDEOMIND_MAX_VIDEO_DURATION_SEC", "3600"))
MAX_VIDEO_WIDTH = int(os.getenv("VIDEOMIND_MAX_VIDEO_WIDTH", "0"))
MAX_VIDEO_HEIGHT = int(os.getenv("VIDEOMIND_MAX_VIDEO_HEIGHT", "0"))
MAX_VIDEO_FPS = float(os.getenv("VIDEOMIND_MAX_VIDEO_FPS", "0"))


# --- Concurrency -----------------------------------------------------------

MAX_CONCURRENT_TASKS = int(os.getenv("VIDEOMIND_MAX_CONCURRENT_TASKS", "4"))


# --- LLM (DeepSeek) --------------------------------------------------------

DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY",
    "",
)
DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL", "deepseek-v4-flash",
)
# --- Planner ----------------------------------------------------------
PLANNER_PROVIDER = os.getenv("VIDEOMIND_PLANNER_PROVIDER", "rule").lower()

# --- LLM (DeepSeek) --------------------------------------------------------
DEEPSEEK_CHAT_URL = os.getenv(
    "DEEPSEEK_CHAT_URL",
    "https://api.deepseek.com/chat/completions",
)




# --- Device (GPU / CPU) ---------------------------------------------------

DEVICE = os.getenv("VIDEOMIND_DEVICE", "auto").lower()  # auto | cuda | cpu

def resolve_device(device_env: str | None = None) -> str:
    """Resolve \"auto\" to \"cuda\" or \"cpu\".  Raises RuntimeError if cuda requested but unavailable."""
    d = (device_env or DEVICE).lower()
    if d == "auto":
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"
    if d == "cuda":
        try:
            import torch
            if not torch.cuda.is_available():
                raise RuntimeError("VIDEOMIND_DEVICE=cuda but CUDA is not available.  Set VIDEOMIND_DEVICE=cpu or omit.")
        except ImportError:
            raise RuntimeError("VIDEOMIND_DEVICE=cuda but PyTorch is not installed.")
    return d

YOLO_DEVICE = resolve_device(os.getenv("VIDEOMIND_YOLO_DEVICE"))
WHISPER_DEVICE = resolve_device(os.getenv("VIDEOMIND_WHISPER_DEVICE"))
WHISPER_COMPUTE_TYPE = os.getenv("VIDEOMIND_WHISPER_COMPUTE_TYPE", "int8_float16" if WHISPER_DEVICE == "cuda" else "int8")
SAM2_DEVICE = resolve_device(os.getenv("VIDEOMIND_SAM2_DEVICE"))


# --- Highlight scoring weights --------------------------------------------

HIGHLIGHT_W_OBJECT = float(os.getenv("VIDEOMIND_HIGHLIGHT_W_OBJECT", "0.25"))
HIGHLIGHT_W_MOTION = float(os.getenv("VIDEOMIND_HIGHLIGHT_W_MOTION", "0.20"))
HIGHLIGHT_W_SPEECH = float(os.getenv("VIDEOMIND_HIGHLIGHT_W_SPEECH", "0.20"))
HIGHLIGHT_W_SCENE = float(os.getenv("VIDEOMIND_HIGHLIGHT_W_SCENE", "0.15"))
HIGHLIGHT_W_QUALITY = float(os.getenv("VIDEOMIND_HIGHLIGHT_W_QUALITY", "0.20"))
HIGHLIGHT_DIVERSITY_LAMBDA = float(os.getenv("VIDEOMIND_HIGHLIGHT_DIVERSITY_LAMBDA", "0.15"))
HIGHLIGHT_MIN_SCORE = float(os.getenv("VIDEOMIND_HIGHLIGHT_MIN_SCORE", "0.0"))
HIGHLIGHT_MIN_DURATION = float(os.getenv("VIDEOMIND_HIGHLIGHT_MIN_DURATION", "3.0"))
HIGHLIGHT_MAX_DURATION = float(os.getenv("VIDEOMIND_HIGHLIGHT_MAX_DURATION", "45.0"))

# Validate weights at import time
_HW_SUM = HIGHLIGHT_W_OBJECT + HIGHLIGHT_W_MOTION + HIGHLIGHT_W_SPEECH + HIGHLIGHT_W_SCENE + HIGHLIGHT_W_QUALITY
if abs(_HW_SUM - 1.0) > 0.01:
    raise ValueError(
        f"Highlight content weights must sum to 1.0, got {_HW_SUM}. "
        f"Check VIDEOMIND_HIGHLIGHT_W_* env vars.  Current values: "
        f"object={HIGHLIGHT_W_OBJECT} motion={HIGHLIGHT_W_MOTION} "
        f"speech={HIGHLIGHT_W_SPEECH} scene={HIGHLIGHT_W_SCENE} "
        f"quality={HIGHLIGHT_W_QUALITY}"
    )
if HIGHLIGHT_DIVERSITY_LAMBDA < 0:
    raise ValueError(f"HIGHLIGHT_DIVERSITY_LAMBDA must be >= 0, got {HIGHLIGHT_DIVERSITY_LAMBDA}")


# --- Server ----------------------------------------------------------------


class Settings:
    app_name: str = "VideoMind Agent"
    debug: bool = os.getenv("VIDEOMIND_DEBUG", "false").lower() == "true"
    host: str = os.getenv("VIDEOMIND_HOST", "0.0.0.0")
    port: int = int(os.getenv("VIDEOMIND_PORT", "8000"))
    database_url: str = os.getenv(
        "VIDEOMIND_DATABASE_URL",
        f"sqlite:///{DATA_DIR / 'videomind.db'}",
    )


settings = Settings()


# --- Task Queue ---
MAX_QUEUE_SIZE = int(os.getenv("VIDEOMIND_MAX_QUEUE_SIZE", "20"))
TASK_TIMEOUT_SEC = int(os.getenv("VIDEOMIND_TASK_TIMEOUT_SEC", "3600"))
STEP_TIMEOUT_SEC = int(os.getenv("VIDEOMIND_STEP_TIMEOUT_SEC", "900"))
TASK_STALE_SEC = int(os.getenv("VIDEOMIND_TASK_STALE_SEC", "1800"))
WORKER_CONCURRENCY = int(os.getenv("VIDEOMIND_WORKER_CONCURRENCY", "1"))


MIN_FREE_DISK_GB = int(os.getenv("VIDEOMIND_MIN_FREE_DISK_GB", "5"))
MAX_TASK_STORAGE_MB = int(os.getenv("VIDEOMIND_MAX_TASK_STORAGE_MB", "2048"))
MONITOR_INTERVAL_SEC = int(os.getenv("VIDEOMIND_MONITOR_INTERVAL_SEC", "30"))