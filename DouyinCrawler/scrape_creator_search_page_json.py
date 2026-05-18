# -*- coding: utf-8 -*-
"""Compatibility wrapper for creator-page internal search.

Prefer the integrated command:
    python main.py creator-search <creator_url> <keyword>
"""

from __future__ import annotations

import argparse
import io
import sys

import config

crawler = None


async def _run(url: str, keyword: str, count: int, headless: bool) -> None:
    global crawler
    from media_platform.douyin import DouYinCrawler

    config.load_from_toml()
    config.apply_cli_args(
        argparse.Namespace(
            command="creator-search",
            urls=[url],
            keyword=keyword,
            count=count,
            headless=headless,
            output=None,
            format=None,
            login=None,
            cookie=None,
            comments_count=None,
            sleep=None,
            no_comments=None,
            with_media=None,
            with_sub_comments=None,
            with_wordcloud=None,
        )
    )
    crawler = DouYinCrawler()
    await crawler.start()


async def _cleanup() -> None:
    if crawler and getattr(crawler, "browser_context", None):
        await crawler.browser_context.close()


def main() -> None:
    if sys.stdout and hasattr(sys.stdout, "buffer"):
        if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr and hasattr(sys.stderr, "buffer"):
        if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("keyword")
    parser.add_argument("-n", "--count", type=int, default=80)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    from tools.app_runner import run

    run(lambda: _run(args.url, args.keyword, args.count, args.headless), _cleanup)


if __name__ == "__main__":
    main()
