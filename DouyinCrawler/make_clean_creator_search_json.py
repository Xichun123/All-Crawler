# -*- coding: utf-8 -*-
import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("-o", "--output", default="")
    args = parser.parse_args()

    source_path = Path(args.source)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    videos = source.get("videos", [])

    clean = {
        "????": source.get("crawl_time", ""),
        "????": "creator_search",
        "?????": source.get("keyword", ""),
        "????": source.get("source_url", ""),
        "???": source.get("final_url", ""),
        "????": source.get("target_count", ""),
        "????": source.get("actual_count", len(videos)),
        "??": source.get("creator", {}),
        "????": [
            {
                "??": item.get("title", ""),
                "????": item.get("video_url", ""),
                "aweme_id": item.get("aweme_id") or item.get("video_id", ""),
            }
            for item in videos
        ],
    }

    if args.output:
        out_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        keyword = clean["?????"] or "keyword"
        out_path = source_path.parent / f"creator_search_{keyword}_{timestamp}_{len(videos)}_clean.json"
    out_path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    print(f"videos={len(videos)}")


if __name__ == "__main__":
    main()
