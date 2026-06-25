import json
import os
from pathlib import Path

from app.config import REPORTS_DIR, CLIPS_DIR, RAW_VIDEOS_DIR


def generate_report(video_id: str) -> dict:
    """Load all available report data and produce a structured JSON + Markdown report.

    Returns dict with keys: json_path, md_path
    """
    report = _build_report_dict(video_id)

    report_dir = REPORTS_DIR / video_id
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = report_dir / "final_report.json"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = report_dir / "final_report.md"
    md_path.write_text(_render_markdown(report, video_id), encoding="utf-8")

    return {"json_path": str(json_path), "md_path": str(md_path)}


# ── Data loader ─────────────────────────────────────


def _load(video_id: str, name: str) -> any:
    p = REPORTS_DIR / video_id / name
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


# ── Build structured dict ───────────────────────────


def _build_report_dict(video_id: str) -> dict:
    scenes = _load(video_id, "scenes.json") or []
    class_stats = _load(video_id, "class_stats.json") or []
    tracks = _load(video_id, "tracks.json") or []
    subtitles = _load(video_id, "subtitles.json") or []
    highlights = _load(video_id, "highlights.json") or []
    metadata = _load(video_id, "metadata.json")
    pipeline = _load(video_id, "pipeline_report.json")

    # Build metadata
    info = metadata or {}
    if not info:
        # Try to read from raw video or previous metadata
        raw_path = RAW_VIDEOS_DIR / f"{video_id}.mp4"
        if raw_path.is_file():
            try:
                from app.services.video_metadata_service import get_video_metadata
                info = get_video_metadata(str(raw_path))
            except Exception:
                pass

    # Gather clip info
    clip_dir = CLIPS_DIR / video_id
    clip_files = sorted([
        f for f in os.listdir(str(clip_dir))
        if f.endswith(".mp4") and f.startswith("clip_")
    ]) if clip_dir.is_dir() else []
    highlight_path = str(clip_dir / "highlight.mp4") if (clip_dir / "highlight.mp4").is_file() else None

    return {
        "video_id": video_id,
        "metadata": info,
        "scenes": scenes,
        "class_statistics": class_stats,
        "track_count": len(tracks),
        "subtitles": subtitles,
        "highlights": highlights,
        "clips": clip_files,
        "highlight_reel": highlight_path,
        "pipeline": pipeline,
    }


# ── Markdown renderer ───────────────────────────────


def _render_markdown(r: dict, video_id: str) -> str:
    lines: list[str] = []
    _add = lambda s="": lines.append(s)

    _add(f"# 视频分析报告 -- `{video_id}`")
    _add()

    # 1. 视频基本信息
    _add("## 1. 视频基本信息")
    meta = r.get("metadata") or {}
    if meta:
        _add(f"- **时长**: {_fmt_time(meta.get('duration', 0))}")
        _add(f"- **分辨率**: {meta.get('width', '?')} x {meta.get('height', '?')}")
        _add(f"- **FPS**: {meta.get('fps', '?')}")
        _add(f"- **总帧数**: {meta.get('frame_count', '?')}")
    else:
        _add("*无元数据*")
    _add()

    # 2. 场景时间轴
    _add("## 2. 场景时间轴")
    scenes = r.get("scenes") or []
    if scenes:
        _add(f"\u68c0\u6d4b\u5230 **{len(scenes)}** 个场景：")
        _add()
        _add("| # | 开始 | 结束 | 时长 |")
        _add("|---|------|------|------|")
        for i, s in enumerate(scenes, 1):
            _add(f"| {i} | {_fmt_time(s['start_time'])} | {_fmt_time(s['end_time'])} | {_fmt_time(s['duration'])} |")
    else:
        _add("*无场景数据*")
    _add()

    # 3. 目标检测统计
    _add("## 3. 目标检测统计")
    stats = r.get("class_statistics") or []
    if stats:
        _add(f"\u68c0\u6d4b\u5230 **{len(stats)}** 类目标：")
        _add()
        _add("| 类别 | 出现次数 | 出现帧数 | 平均置信度 |")
        _add("|------|----------|----------|------------|")
        for c in sorted(stats, key=lambda x: -x['total_occurrences']):
            _add(f"| {c['class_name']} | {c['total_occurrences']} | {c['frame_count']} | {c['avg_confidence']:.3f} |")
        _add()
        _add(f"\u603b\u8f68\u8ff9\u6570\uff1a**{r.get('track_count', 0)}**”")
    else:
        _add("*无检测数据*")
    _add()

    # 4. 字幕摘要
    _add("## 4. 字幕摘要")
    subs = r.get("subtitles") or []
    if subs:
        total_text = " ".join(s["text"] for s in subs)
        _add(f"- **字幕段数**: {len(subs)}")
        _add(f"- **总字数**: ~{len(total_text)}")
        _add()
        _add("### 示例文本")
        _add()
        _add("| 时间 | 内容 |")
        _add("|------|------|")
        for s in subs[:8]:
            _add(f"| {_fmt_time(s['start'])} | {s['text']} |")
        if len(subs) > 8:
            _add(f"| ... | *\uff08\u8fd8\u6709 {len(subs) - 8} 段）* |")
    else:
        _add("*无字幕（视频可能没有音轨或转录被跳过）*")
    _add()

    # 5. 精彩片段推荐
    _add("## 5. 精彩片段推荐")
    highlights = r.get("highlights") or []
    if highlights:
        _add(f"推荐 **{len(highlights)}** 个精彩片段：")
        _add()
        _add("| # | 开始 | 结束 | 时长 | 评分 | 理由 |")
        _add("|---|------|------|------|------|------|")
        for i, h in enumerate(highlights, 1):
            reasons = ", ".join(h.get("reason", []))
            _add(f"| {i} | {_fmt_time(h['start_time'])} | {_fmt_time(h['end_time'])} | {_fmt_time(h['duration'])} | {h.get('score', 0):.3f} | {reasons} |")
    else:
        _add("*未生成精彩片段*")
    _add()

    # 6. 导出剪辑
    _add("## 6. 导出剪辑")
    clips = r.get("clips") or []
    reel = r.get("highlight_reel")
    if clips:
        _add(f"- **独立片段**: {len(clips)} 个")
        for c in clips:
            _add(f"  - `{c}`")
        if reel:
            _add(f"- **精彩合辑**: `highlight.mp4`")
    else:
        _add("*未导出剪辑*")
    _add()
    _add("---")
    _add("*由 VideoMind Agent 生成*")

    return "\n".join(lines)

# ── Helpers ─────────────────────────────────────────


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
