"""Loader registry. Add a new platform by registering it here."""

from __future__ import annotations

from pathlib import Path

from ..schema import Video
from .base import BaseLoader
from .douyin import DouyinLoader


_REGISTRY: dict[str, type[BaseLoader]] = {
    DouyinLoader.platform: DouyinLoader,
    # Future:
    # "bilibili": BilibiliLoader,
    # "kuaishou": KuaishouLoader,
    # "weibo": WeiboLoader,
    # "xhs": XhsLoader,
}


def available_platforms() -> list[str]:
    return sorted(_REGISTRY)


def load_platform(platform: str, data_dir: Path) -> list[Video]:
    """Load every file under ``data_dir`` using the loader for ``platform``."""
    if platform not in _REGISTRY:
        raise KeyError(
            f"No loader registered for {platform!r}. "
            f"Known: {available_platforms()}"
        )
    loader = _REGISTRY[platform]()
    return loader.load_dir(Path(data_dir))


__all__ = ["BaseLoader", "available_platforms", "load_platform"]
