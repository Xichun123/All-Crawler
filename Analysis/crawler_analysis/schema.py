"""Canonical video schema shared across all platform loaders."""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any


VIDEO_COLUMNS = [
    "platform",
    "video_id",
    "url",
    "author",
    "title",
    "publish_time",
    "likes",
    "collects",
    "comments",
    "shares",
    "is_ai",
]


@dataclass
class Video:
    """Normalized video record. Missing metrics are None, not 0."""

    platform: str
    video_id: str
    url: str
    title: str
    likes: int | None = None
    comments: int | None = None
    shares: int | None = None
    collects: int | None = None
    author: str | None = None
    publish_time: datetime | None = None
    is_ai: bool | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_row(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("raw", None)
        if self.publish_time is not None:
            d["publish_time"] = self.publish_time.isoformat()
        return d
