"""Base class and registry for platform-specific loaders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable

from ..schema import Video


class BaseLoader(ABC):
    """Read raw crawler output for one platform and yield normalized Video records.

    Subclasses set ``platform`` and implement ``load_file`` for one input file.
    """

    platform: str = ""
    file_glob: tuple[str, ...] = ("*.json",)

    @abstractmethod
    def load_file(self, path: Path) -> Iterable[Video]:
        """Parse a single crawler output file into Video records."""

    def load_dir(self, root: Path) -> list[Video]:
        videos: list[Video] = []
        for pattern in self.file_glob:
            for path in sorted(root.glob(pattern)):
                videos.extend(self.load_file(path))
        return videos
