# -*- coding: utf-8 -*-
"""Convert creator-search raw JSON to the clean project output format."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.clean_writer import write_creator_search_result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("-o", "--output", default="")
    args = parser.parse_args()

    source_path = Path(args.source)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    videos = source.get("videos", [])

    if args.output:
        output_path = Path(args.output)
        output_dir = str(output_path.parent)
        result_path = write_creator_search_result(
            creator=source.get("creator", {}),
            keyword=source.get("keyword", ""),
            source_url=source.get("source_url", ""),
            final_url=source.get("final_url", ""),
            target_count=source.get("target_count", len(videos)),
            videos_raw=videos,
            output_dir=output_dir,
        )
        Path(result_path).replace(output_path)
        result_path = str(output_path)
    else:
        result_path = write_creator_search_result(
            creator=source.get("creator", {}),
            keyword=source.get("keyword", ""),
            source_url=source.get("source_url", ""),
            final_url=source.get("final_url", ""),
            target_count=source.get("target_count", len(videos)),
            videos_raw=videos,
            output_dir=str(source_path.parent),
        )

    print(result_path)
    print(f"videos={len(videos)}")


if __name__ == "__main__":
    main()
