"""Create label templates for real highlight evaluation datasets.

Modes:
  video    — create an empty label template for a single video
  batch    — create multiple templates from a CSV manifest
  timeline — create a timeline-based template with evenly spaced segments

Output: JSON file ready for manual annotation.
"""

import argparse, csv, json, math, sys
from datetime import timedelta
from pathlib import Path


LABEL_CATEGORIES = ["speech", "visual", "action", "scene", "mixed", "other"]
LABEL_RATING_MIN = 1
LABEL_RATING_MAX = 5


def _format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS.mmm."""
    td = timedelta(seconds=seconds)
    total = td.total_seconds()
    hours = int(total // 3600)
    minutes = int((total % 3600) // 60)
    secs = total % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def create_video_template(video_id: str, duration: float, category: str = "",
                          video_path: str = "", num_segments: int = 0) -> dict:
    """Create a label template for one video.

    Args:
        video_id: Unique video identifier.
        duration: Video duration in seconds.
        category: Optional video category (lecture, interview, sports, etc.).
        video_path: Optional path to video file.
        num_segments: If > 0, pre-fill evenly spaced empty segments.

    Returns:
        Template dict with empty labels array.
    """
    if duration <= 0:
        raise ValueError(f"Duration must be > 0, got {duration}")
    if num_segments < 0:
        raise ValueError(f"num_segments must be >= 0, got {num_segments}")

    labels = []
    if num_segments > 0:
        segment_dur = duration / num_segments
        for i in range(num_segments):
            st = round(i * segment_dur, 2)
            et = round((i + 1) * segment_dur, 2)
            labels.append({
                "id": f"gt_{i+1:03d}",
                "start_time": st,
                "end_time": et,
                "rating": 3,
                "category": "",
                "note": "",
            })

    return {
        "video_id": video_id,
        "video_path": video_path,
        "duration": duration,
        "generated_at": datetime_now_iso(),
        "annotator": "",
        "video_category": category,
        "labels": labels,
    }


def datetime_now_iso() -> str:
    """Return current UTC time in ISO format."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def create_batch_templates(csv_path: str, output_dir: str, dry_run: bool = False) -> list[dict]:
    """Create label templates from a CSV manifest.

    CSV columns: video_id, duration, category, video_path (optional)
    """
    templates = []
    out = Path(output_dir)
    if not dry_run:
        out.mkdir(parents=True, exist_ok=True)

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vid = row["video_id"].strip()
            dur = float(row["duration"])
            cat = row.get("category", "").strip()
            vpath = row.get("video_path", "").strip()

            if not vid:
                continue
            if dur <= 0:
                print(f"  WARNING: {vid} has invalid duration {dur}, skipping")
                continue

            template = create_video_template(
                video_id=vid, duration=dur, category=cat, video_path=vpath
            )
            templates.append(template)

            if not dry_run:
                filename = f"{vid}_label_template.json"
                (out / filename).write_text(
                    json.dumps(template, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

    return templates


def create_timeline_template(video_id: str, duration: float,
                              interval: float = 10.0, category: str = "",
                              video_path: str = "") -> dict:
    """Create a label template with evenly spaced timeline segments.

    Each segment is an empty annotation slot. Useful for frame-by-frame or
    fixed-interval annotation workflows.

    Args:
        video_id: Unique video identifier.
        duration: Video duration in seconds.
        interval: Segment interval in seconds.
        category: Optional video category.
        video_path: Optional path to video file.

    Returns:
        Template dict with timeline segments as labels.
    """
    num_segments = max(1, int(math.ceil(duration / interval)))
    return create_video_template(
        video_id=video_id,
        duration=duration,
        category=category,
        video_path=video_path,
        num_segments=num_segments,
    )


def validate_label(label: dict, idx: int, duration: float) -> list[str]:
    """Validate a single label entry, return error messages.

    Returns empty list if valid.
    """
    errors = []
    st = label.get("start_time")
    et = label.get("end_time")
    rating = label.get("rating")
    cat = label.get("category", "")

    if st is None or not isinstance(st, (int, float)):
        errors.append(f"Label {idx}: invalid or missing start_time")
    elif st < 0:
        errors.append(f"Label {idx}: start_time {st} < 0")

    if et is None or not isinstance(et, (int, float)):
        errors.append(f"Label {idx}: invalid or missing end_time")
    elif et <= (st or 0):
        errors.append(f"Label {idx}: end_time {et} <= start_time {st}")

    if duration > 0 and (et or 0) > duration:
        errors.append(f"Label {idx}: end_time {et} exceeds duration {duration}")

    if rating is not None:
        if not isinstance(rating, int) or rating < LABEL_RATING_MIN or rating > LABEL_RATING_MAX:
            errors.append(f"Label {idx}: rating {rating} not in [{LABEL_RATING_MIN},{LABEL_RATING_MAX}]")

    if cat and cat not in LABEL_CATEGORIES:
        errors.append(f"Label {idx}: unknown category '{cat}'. Allowed: {LABEL_CATEGORIES}")

    return errors


def validate_label_file(path: str) -> list[str]:
    """Validate a complete label file, return error messages.

    Returns empty list if valid.
    """
    errors = []
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as e:
        return [f"Cannot read {path}: {e}"]

    vid = data.get("video_id", "")
    if not vid:
        errors.append("Missing or empty video_id")

    duration = data.get("duration", 0)
    if not duration or not isinstance(duration, (int, float)) or duration <= 0:
        errors.append(f"Invalid duration: {duration}")

    labels = data.get("labels", [])
    if not labels:
        errors.append("No labels found (empty or missing labels array)")

    for i, label in enumerate(labels):
        errors.extend(validate_label(label, i, duration))

    # Check for duplicate IDs
    ids = [lbl.get("id") for lbl in labels if lbl.get("id")]
    if len(ids) != len(set(ids)):
        errors.append("Duplicate label IDs found")

    return errors


# ── Main ─────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Create and validate label templates for highlight evaluation."
    )
    parser.add_argument("--mode", choices=["video", "batch", "timeline", "validate"],
                        default="video", help="Operation mode")

    # Video / timeline mode args
    parser.add_argument("--video-id", type=str, default="",
                        help="Video identifier")
    parser.add_argument("--duration", type=float, default=0,
                        help="Video duration in seconds")
    parser.add_argument("--category", type=str, default="",
                        help="Video category (lecture, interview, sports, etc.)")
    parser.add_argument("--video-path", type=str, default="",
                        help="Optional path to video file")
    parser.add_argument("--segments", type=int, default=0,
                        help="Number of pre-filled empty segments (video mode)")
    parser.add_argument("--interval", type=float, default=10.0,
                        help="Segment interval in seconds (timeline mode, default: 10s)")

    # Batch mode args
    parser.add_argument("--csv", type=str, default="",
                        help="CSV file for batch mode")
    parser.add_argument("--output-dir", type=str, default="",
                        help="Output directory for generated templates")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate CSV without writing files")

    # Validate mode args
    parser.add_argument("--label-file", type=str, default="",
                        help="Label file to validate")

    args = parser.parse_args()

    if args.mode == "video":
        if not args.video_id or args.duration <= 0:
            print("ERROR: video mode requires --video-id and --duration > 0")
            sys.exit(1)

        template = create_video_template(
            video_id=args.video_id,
            duration=args.duration,
            category=args.category,
            video_path=args.video_path,
            num_segments=args.segments,
        )

        output_path = args.output_dir or "."
        out = Path(output_path)
        out.mkdir(parents=True, exist_ok=True)
        filename = f"{args.video_id}_label_template.json"
        (out / filename).write_text(
            json.dumps(template, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Created label template: {out / filename}")
        print(f"  Video: {args.video_id}, duration: {args.duration}s")
        print(f"  Labels: {len(template['labels'])} (empty, ready for annotation)")
        print(f"  Template path: {out / filename}")

    elif args.mode == "timeline":
        if not args.video_id or args.duration <= 0:
            print("ERROR: timeline mode requires --video-id and --duration > 0")
            sys.exit(1)

        template = create_timeline_template(
            video_id=args.video_id,
            duration=args.duration,
            interval=args.interval,
            category=args.category,
            video_path=args.video_path,
        )

        output_path = args.output_dir or "."
        out = Path(output_path)
        out.mkdir(parents=True, exist_ok=True)
        filename = f"{args.video_id}_label_template.json"
        (out / filename).write_text(
            json.dumps(template, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Created timeline label template: {out / filename}")
        print(f"  Video: {args.video_id}, duration: {args.duration}s")
        print(f"  Interval: {args.interval}s, segments: {len(template['labels'])}")

    elif args.mode == "batch":
        if not args.csv:
            print("ERROR: batch mode requires --csv")
            sys.exit(1)

        templates = create_batch_templates(
            csv_path=args.csv,
            output_dir=args.output_dir or ".",
            dry_run=args.dry_run,
        )

        if args.dry_run:
            print(f"Dry run: validated {len(templates)} videos from {args.csv}")
        else:
            print(f"Created {len(templates)} label templates in {args.output_dir or '.'}")
        for t in templates:
            print(f"  {t['video_id']}: {t['duration']}s, {len(t['labels'])} labels"
                  f"{', category: ' + t.get('video_category', '') if t.get('video_category') else ''}")

    elif args.mode == "validate":
        if not args.label_file:
            print("ERROR: validate mode requires --label-file")
            sys.exit(1)

        errors = validate_label_file(args.label_file)
        if not errors:
            print(f"Label file {args.label_file} is VALID")
            data = json.loads(Path(args.label_file).read_text(encoding="utf-8"))
            print(f"  Video: {data.get('video_id', '?')}, duration: {data.get('duration', '?')}s")
            print(f"  Labels: {len(data.get('labels', []))}")
        else:
            print(f"Label file {args.label_file} has {len(errors)} ERROR(S):")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
