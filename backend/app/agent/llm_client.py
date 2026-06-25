"""Lightweight DeepSeek / OpenAI-compatible chat client.

Uses ``urllib`` from stdlib so no extra dependency is required.
"""

import json
import urllib.request
from typing import Optional

import logging

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_CHAT_URL

logger = logging.getLogger(__name__)


# ── System prompt for the planner ───────────────────

TOOL_DESCRIPTIONS = """
Available tools and what they do:

  metadata             – Extract video duration, fps, resolution, frame count
  extract_frames       – Extract still frames from video at a given fps
  detect_scenes        – Detect shot/scene boundaries using PySceneDetect
  detect_objects       – Run YOLO object detection on extracted frames
  track_objects        – Track detected objects across frames (ByteTrack)
  transcribe           – Extract audio and run speech-to-text (faster-whisper)
  recommend_highlights – Score and rank highlight segments from the video
  export_clips         – Cut highlight segments from the original video
  generate_report      – Produce a structured JSON + Markdown analysis report

Dependency rules:
  detect_objects   → extract_frames must run first
  track_objects    → detect_objects must run first
  recommend_highlights → detect_scenes, detect_objects, track_objects must run first
  export_clips     → recommend_highlights must run first
  generate_report  → metadata, detect_scenes, detect_objects, track_objects, recommend_highlights must run first

Always include "metadata" at the start.
Only use tools from the list above.
"""

PLANNER_SYSTEM_PROMPT = (
    "You are a video analysis planner. Given a user goal, select the minimal "
    "set of tools needed and return them in execution order as a JSON array of strings."
    + TOOL_DESCRIPTIONS
)


# ── API call ────────────────────────────────────────


def _build_payload(user_goal: str) -> dict:
    return {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {"role": "user", "content": f"User goal: {user_goal}\n\nReturn only a JSON array of tool names."},
        ],
        "temperature": 0.1,
        "max_tokens": 256,
    }


def call_llm_planner(user_goal: str) -> Optional[list[str]]:
    """Call DeepSeek to generate a tool plan. Returns None on failure."""
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY.startswith("sk-") is False:
        logger.info("DEEPSEEK_API_KEY not configured -- planner will use rule-based fallback")
        return None

    payload = _build_payload(user_goal)
    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        DEEPSEEK_CHAT_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            content = body["choices"][0]["message"]["content"].strip()
            # Strip markdown code fences if present
            if content.startswith("```"):
                lines = content.splitlines()
                content = "\n".join(l for l in lines if not l.startswith("```"))
            result = json.loads(content)
            if isinstance(result, list) and all(isinstance(t, str) for t in result):
                return result
            return None
    except Exception:
        return None
