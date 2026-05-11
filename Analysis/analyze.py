"""End-to-end video interaction metrics analysis CLI.

Current scope: video-level likes, comments count, and shares. Prefer
crawler ``creator`` outputs for this stage because they contain many videos
from one creator/account and are suitable for descriptive statistics.

``detail`` outputs are still readable, but comment text is intentionally
ignored here. If creator and detail files contain the same video, rows are
deduplicated by URL. A later NLP stage should build a separate comment-level
pipeline from detail-mode comment lists.

Layout:
    data/{platform}/*.json     ← raw crawler output, creator preferred
    labels/{platform}.csv      ← human-edited AI/non-AI labels
    reports/                   ← generated markdown + charts

Typical flow:
  1. Drop creator-mode crawler JSON into data/{platform}/.
  2. Run ``python analyze.py --refresh-labels``. This generates label CSV
     templates with empty ``is_ai`` columns. Fill them in.
  3. Run ``python analyze.py`` again to produce reports/report.md and PNGs.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from crawler_analysis import (
    available_platforms,
    load_platform,
    load_labels,
    merge_labels,
    write_label_template,
)
from crawler_analysis.stats import (
    render_charts,
    render_report,
    videos_to_dataframe,
)


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LABELS_DIR = ROOT / "labels"
REPORTS_DIR = ROOT / "reports"


def discover_platforms(data_dir: Path) -> list[str]:
    if not data_dir.exists():
        return []
    return sorted(
        d.name
        for d in data_dir.iterdir()
        if d.is_dir() and any(d.glob("*.json"))
    )


def cmd_run(args: argparse.Namespace) -> int:
    platforms = args.platforms or discover_platforms(DATA_DIR)
    if not platforms:
        print(f"No platform data found under {DATA_DIR}/", file=sys.stderr)
        return 1

    known = set(available_platforms())
    unknown = [p for p in platforms if p not in known]
    if unknown:
        print(
            f"No loader registered for: {unknown}. "
            f"Known: {sorted(known)}",
            file=sys.stderr,
        )
        return 2

    all_videos = []
    for platform in platforms:
        videos = load_platform(platform, DATA_DIR / platform)
        # Dedupe within platform by URL (creator + detail can overlap).
        seen: set[str] = set()
        unique = []
        for v in videos:
            if v.url and v.url not in seen:
                seen.add(v.url)
                unique.append(v)
        videos = unique

        label_path = LABELS_DIR / f"{platform}.csv"
        if args.refresh_labels or not label_path.exists():
            total, added = write_label_template(label_path, videos)
            print(
                f"[{platform}] label template: {label_path} "
                f"({total} rows, {added} new)"
            )

        labels = load_labels(label_path)
        merge_labels(videos, labels)
        all_videos.extend(videos)
        print(f"[{platform}] loaded {len(videos)} videos")

    df = videos_to_dataframe(all_videos)
    if df.empty:
        print("No videos loaded.", file=sys.stderr)
        return 3

    if args.csv:
        out_csv = REPORTS_DIR / "videos.csv"
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_csv, index=False)
        print(f"wrote {out_csv}")

    chart_paths = render_charts(df, REPORTS_DIR / "charts")
    report_path = render_report(
        df, REPORTS_DIR / "report.md", chart_paths=chart_paths
    )
    print(f"wrote {report_path}")
    for p in chart_paths:
        print(f"wrote {p}")

    unlabeled = df["is_ai"].isna().sum()
    if unlabeled:
        print(
            f"\n[!] {unlabeled} video(s) still have no AI label. "
            f"Edit the label CSVs under {LABELS_DIR}/ and rerun."
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platforms",
        nargs="*",
        help="Subset of platforms to analyze (default: auto-discover from data/).",
    )
    parser.add_argument(
        "--refresh-labels",
        action="store_true",
        help="Regenerate label CSV templates (preserves existing rows).",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Also dump the merged videos table to reports/videos.csv.",
    )
    args = parser.parse_args(argv)
    return cmd_run(args)


if __name__ == "__main__":
    raise SystemExit(main())
