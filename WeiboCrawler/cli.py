# -*- coding: utf-8 -*-
# CLI 子命令解析 — argparse 实现，零新依赖

import argparse
import sys


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    """为子命令添加公共选项"""
    parser.add_argument(
        "-o", "--output", default=None,
        help="输出目录 (默认: ./data)",
    )
    parser.add_argument(
        "-f", "--format", default=None, choices=["json", "csv"],
        help="存储格式 (默认: json)",
    )
    parser.add_argument(
        "--login", default=None, choices=["qrcode", "cookie"],
        help="登录方式 (默认: qrcode)",
    )
    parser.add_argument(
        "--cookie", default=None,
        help="Cookie 字符串 (配合 --login cookie 使用)",
    )
    parser.add_argument(
        "--headless", action="store_true", default=None,
        help="无头浏览器模式",
    )
    parser.add_argument(
        "--no-comments", action="store_true", default=None,
        help="不爬评论",
    )
    parser.add_argument(
        "--with-media", action="store_true", default=None,
        help="下载图片",
    )
    parser.add_argument(
        "--with-sub-comments", action="store_true", default=None,
        help="爬二级评论",
    )
    parser.add_argument(
        "--with-wordcloud", action="store_true", default=None,
        help="生成词云",
    )
    parser.add_argument(
        "--full-text", action="store_true", default=None,
        help="获取长微博全文 (默认开启)",
    )
    parser.add_argument(
        "--no-full-text", action="store_true", default=None,
        help="不获取长微博全文",
    )
    parser.add_argument(
        "-n", "--count", type=int, default=None,
        help="爬取数量上限 (默认: 20)",
    )
    parser.add_argument(
        "--comments-count", type=int, default=None,
        help="单帖子评论数上限 (默认: 10)",
    )
    parser.add_argument(
        "--sleep", type=float, default=None,
        help="爬取间隔秒数 (默认: 2)",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python main.py",
        description="微博爬虫 — 支持搜索、帖子详情、创作者主页三种模式",
        epilog=(
            "示例:\n"
            '  python main.py search "Python" "编程"\n'
            '  python main.py detail "4982041758140155"\n'
            '  python main.py creator "5756404150"\n'
            "  python main.py                  # 无参数 → 读取 config.toml 运行\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command")

    # ---- search ----
    search_parser = subparsers.add_parser(
        "search", help="关键词搜索模式",
        description="按关键词搜索微博帖子",
    )
    search_parser.add_argument(
        "keywords", nargs="+",
        help="搜索关键词列表",
    )
    search_parser.add_argument(
        "--search-type", default=None,
        choices=["default", "real_time", "popular", "video"],
        help="搜索类型 (默认: default)",
    )
    _add_common_options(search_parser)

    # ---- detail ----
    detail_parser = subparsers.add_parser(
        "detail", help="帖子详情模式",
        description="爬取指定微博帖子的详情数据",
    )
    detail_parser.add_argument(
        "ids", nargs="+",
        help="微博帖子 ID 列表",
    )
    _add_common_options(detail_parser)

    # ---- creator ----
    creator_parser = subparsers.add_parser(
        "creator", help="创作者主页模式",
        description="爬取指定微博用户的主页数据",
    )
    creator_parser.add_argument(
        "ids", nargs="+",
        help="微博用户 ID 列表",
    )
    _add_common_options(creator_parser)

    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace | None:
    """解析命令行参数。无子命令时返回 None（由 config.toml 驱动）。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        return None
    return args
