"""GPU / CUDA environment diagnostic.

Run from project root:
    python scripts/check_gpu.py

No secrets or API keys are printed.
"""
import sys
from pathlib import Path

# Make backend/ importable regardless of cwd
_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_DIR = _SCRIPT_DIR.parent / "backend"
sys.path.insert(0, str(_BACKEND_DIR))


def _check(label, ok, detail=""):
    status = "OK" if ok else "MISSING"
    print(f"  [{status}] {label}")
    if detail:
        for line in detail.strip().split("\n"):
            print(f"          {line}")


def main():
    print("=" * 56)
    print("  VideoMind Agent -- GPU / Device Diagnostic")
    print("=" * 56)
    print()

    # 1. Python
    print("[1] Python")
    print(f"  Executable:  {sys.executable}")
    print(f"  Version:     {sys.version.split()[0]}")
    print()

    # 2. PyTorch / CUDA
    print("[2] PyTorch / CUDA")
    try:
        import torch
        print(f"  PyTorch version:  {torch.__version__}")
        cuda_avail = torch.cuda.is_available()
        _check("torch.cuda.is_available()", cuda_avail)
        if cuda_avail:
            print(f"  CUDA version:     {torch.version.cuda}")
            print(f"  GPU count:        {torch.cuda.device_count()}")
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                props = torch.cuda.get_device_properties(i)
                vram_gb = props.total_memory / 1024**3
                print(f"  GPU [{i}]:  {name}  (VRAM: {vram_gb:.1f} GB)")
        else:
            import subprocess
            try:
                r = subprocess.run([sys.executable, "-c", "import torch; print(torch.__version__)"],
                                   capture_output=True, text=True, timeout=10)
                print(f"  (torch is installed: {r.stdout.strip()})")
            except Exception:
                pass
            _check("nvidia-smi", False, "Run 'nvidia-smi' to check driver or install CUDA toolkit")
    except ImportError:
        _check("PyTorch installed", False, "conda install pytorch  or  pip install torch")
    print()

    # 3. CTranslate2 (faster-whisper)
    print("[3] CTranslate2 (faster-whisper)")
    try:
        import ctranslate2
        print(f"  Version:  {getattr(ctranslate2, '__version__', 'unknown')}")
        try:
            dev_count = ctranslate2.get_cuda_device_count()
            _check(f"CUDA device count = {dev_count}", dev_count > 0)
        except Exception as e:
            _check("CUDA support", False, str(e))
    except ImportError:
        _check("ctranslate2 installed", False, "pip install ctranslate2  (comes with faster-whisper)")
    print()

    # 4. Ultralytics YOLO
    print("[4] Ultralytics YOLO")
    try:
        import ultralytics
        print(f"  Version:  {ultralytics.__version__}")
    except ImportError:
        _check("ultralytics installed", False, "pip install ultralytics")
    print()

    # 5. VideoMind resolved device configuration
    print("[5] VideoMind device configuration")
    try:
        from app.config import (
            DEVICE, YOLO_DEVICE, WHISPER_DEVICE,
            WHISPER_COMPUTE_TYPE, SAM2_DEVICE,
        )
        print(f"  VIDEOMIND_DEVICE (from env, default=auto):     {DEVICE}")
        print(f"  VIDEOMIND_YOLO_DEVICE (resolved):             {YOLO_DEVICE}")
        print(f"  VIDEOMIND_WHISPER_DEVICE (resolved):          {WHISPER_DEVICE}")
        print(f"  VIDEOMIND_WHISPER_COMPUTE_TYPE (from env):    {WHISPER_COMPUTE_TYPE}")
        print(f"  VIDEOMIND_SAM2_DEVICE (resolved):             {SAM2_DEVICE}")

        # Also show per-model env vars (raw, before resolve)
        import os
        print()
        print(f"  VIDEOMIND_YOLO_DEVICE env var:      {os.environ.get('VIDEOMIND_YOLO_DEVICE', '(not set)')}")
        print(f"  VIDEOMIND_WHISPER_DEVICE env var:   {os.environ.get('VIDEOMIND_WHISPER_DEVICE', '(not set)')}")
        print(f"  VIDEOMIND_SAM2_DEVICE env var:      {os.environ.get('VIDEOMIND_SAM2_DEVICE', '(not set)')}")
        print(f"  VIDEOMIND_WHISPER_COMPUTE_TYPE env: {os.environ.get('VIDEOMIND_WHISPER_COMPUTE_TYPE', '(not set)')}")
    except Exception as e:
        print(f"  (config not importable: {e})")
    print()

    print("=" * 56)
    print("  Diagnostic complete.")
    print("=" * 56)


if __name__ == "__main__":
    main()
