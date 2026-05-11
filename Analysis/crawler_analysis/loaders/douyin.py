"""Douyin loader.

Supports two output shapes from DouyinCrawler:
  - creator mode: top-level dict with ``作者`` and ``视频列表``
  - detail mode: top-level dict with ``视频列表`` (each item carries ``作者昵称``)

For the current video interaction metrics stage (likes / comments count /
shares), creator mode is preferred because it provides a larger video list per
creator/account. Detail mode is accepted only to reuse its per-video metric
fields; comment text is ignored here and should be handled later by a separate
comment-level NLP pipeline.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..schema import Video
from .base import BaseLoader


_VIDEO_ID_RE = re.compile(r"/video/(\d+)")


def _parse_time(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _video_id_from_url(url: str) -> str:
    m = _VIDEO_ID_RE.search(url or "")
    return m.group(1) if m else (url or "")


class DouyinLoader(BaseLoader):
    platform = "douyin"

    def load_file(self, path: Path) -> Iterable[Video]:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)

        default_author = None
        author_block = data.get("作者")
        if isinstance(author_block, dict):
            default_author = author_block.get("昵称")

        for item in data.get("视频列表", []):
            url = item.get("视频链接", "")
            video_id = _video_id_from_url(url)
            # Skip placeholder rows the crawler emits for deleted/private videos:
            # empty URL or URL with no numeric id. They have no analyzable metrics.
            if not video_id.isdigit():
                continue
            yield Video(
                platform=self.platform,
                video_id=video_id,
                url=url,
                title=item.get("标题", ""),
                likes=item.get("点赞数"),
                comments=item.get("评论数"),
                shares=item.get("分享数"),
                collects=item.get("收藏数"),
                author=item.get("作者昵称") or default_author,
                publish_time=_parse_time(item.get("发布时间")),
                raw=item,
            )
