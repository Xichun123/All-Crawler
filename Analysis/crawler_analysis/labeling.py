"""AI/non-AI labeling.

Labels live in ``labels/{platform}.csv`` with columns:
    url, is_ai, note

``is_ai`` accepts: 1/0, true/false, yes/no, ai/human, empty (= unlabeled).
The CSV is the human-edited source of truth; this module never overwrites
existing rows when refreshing a template — it only appends new videos.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from .schema import Video


LABEL_COLUMNS = ["url", "is_ai", "note", "title", "author"]

# utf-8-sig writes a BOM so Excel on macOS/Windows opens the file as UTF-8
# instead of guessing a legacy encoding. csv.DictReader transparently strips
# the BOM, so the same encoding works for both reading and writing.
_LABEL_ENCODING = "utf-8-sig"


_TRUE = {"1", "true", "yes", "y", "ai", "t"}
_FALSE = {"0", "false", "no", "n", "human", "non-ai", "f"}


def _parse_bool(s: str) -> bool | None:
    s = (s or "").strip().lower()
    if not s:
        return None
    if s in _TRUE:
        return True
    if s in _FALSE:
        return False
    raise ValueError(f"Cannot parse is_ai value: {s!r}")


def load_labels(path: Path) -> dict[str, bool | None]:
    """Read a label CSV. Returns {url: is_ai_or_None}."""
    path = Path(path)
    if not path.exists():
        return {}
    out: dict[str, bool | None] = {}
    with path.open(encoding=_LABEL_ENCODING) as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = (row.get("url") or "").strip()
            if not url:
                continue
            out[url] = _parse_bool(row.get("is_ai", ""))
    return out


def write_label_template(
    path: Path, videos: Iterable[Video], *, refresh: bool = True
) -> tuple[int, int]:
    """Write/refresh a label template CSV.

    Existing rows are preserved (their ``is_ai``/``note`` values stay).
    New videos get appended with empty ``is_ai``.

    Returns ``(total_rows, newly_added)``.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, dict[str, str]] = {}
    if path.exists() and refresh:
        with path.open(encoding=_LABEL_ENCODING) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = (row.get("url") or "").strip()
                if url:
                    existing[url] = row

    new_count = 0
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for v in videos:
        if v.url in seen:
            continue
        seen.add(v.url)
        if v.url in existing:
            row = existing[v.url]
            row["title"] = v.title or row.get("title", "")
            row["author"] = v.author or row.get("author", "")
        else:
            row = {
                "url": v.url,
                "is_ai": "",
                "note": "",
                "title": v.title or "",
                "author": v.author or "",
            }
            new_count += 1
        rows.append(row)

    rows.sort(key=lambda r: r["url"])
    with path.open("w", encoding=_LABEL_ENCODING, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LABEL_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in LABEL_COLUMNS})

    return len(rows), new_count


def merge_labels(videos: list[Video], labels: dict[str, bool | None]) -> list[Video]:
    """Stamp ``is_ai`` onto each video from the label map. Returns the same list."""
    for v in videos:
        if v.url in labels:
            v.is_ai = labels[v.url]
    return videos
