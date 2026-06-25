#!/usr/bin/env python3
"""Standalone script to check video metadata using the metadata service.

Usage:
    python scripts/check_video_metadata.py <video_path>
"""

import sys
import json
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.services.video_metadata_service import get_video_metadata  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_video_metadata.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    if not Path(video_path).is_file():
        print(f"File not found: {video_path}")
        sys.exit(1)

    try:
        meta = get_video_metadata(video_path)
        print(json.dumps(meta, indent=2))
    except Exception as e:
        print(f"Error reading metadata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
