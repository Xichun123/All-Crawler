# -*- coding: utf-8 -*-
from .base_config import *

import os
import re
import tomllib


def _extract_weibo_id(raw: str) -> str:
    """从 URL 或纯 ID 字符串中提取微博数字 ID。

    支持格式:
      - 纯数字: "1778742953"
      - 个人主页 URL: "https://m.weibo.cn/profile/1778742953?..."
      - 帖子详情 URL: "https://m.weibo.cn/detail/5265648960942931"
    """
    raw = raw.strip()
    if raw.isdigit():
        return raw
    m = re.search(r"(?:profile|detail|status)/(\d+)", raw)
    if m:
        return m.group(1)
    # 兜底：尝试提取第一段连续数字（≥6位）
    m = re.search(r"(\d{6,})", raw)
    if m:
        return m.group(1)
    return raw


# TOML key → config module variable 映射
_TOML_KEY_MAP = {
    "mode":              "CRAWLER_TYPE",
    "keywords":          "KEYWORDS",           # list → 逗号拼接字符串
    "note_ids":          "WEIBO_SPECIFIED_ID_LIST",
    "creator_ids":       "WEIBO_CREATOR_ID_LIST",
    "login":             "LOGIN_TYPE",
    "cookie":            "COOKIES",
    "format":            "SAVE_DATA_OPTION",
    "output":            "SAVE_DATA_PATH",
    "count":             "CRAWLER_MAX_NOTES_COUNT",
    "comments_count":    "CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES",
    "comments":          "ENABLE_GET_COMMENTS",
    "sub_comments":      "ENABLE_GET_SUB_COMMENTS",
    "media":             "ENABLE_GET_MEIDAS",
    "wordcloud":         "ENABLE_GET_WORDCLOUD",
    "headless":          "HEADLESS",
    "sleep":             "CRAWLER_MAX_SLEEP_SEC",
    "proxy":             "ENABLE_IP_PROXY",
    "search_type":       "WEIBO_SEARCH_TYPE",
    "full_text":         "ENABLE_WEIBO_FULL_TEXT",
}


def _set(name: str, value: object) -> None:
    """设置当前模块级变量"""
    globals()[name] = value
    # 同步到 base_config / wb_config，使 from config.xxx import YYY 也能拿到新值
    from . import base_config, wb_config
    for mod in (base_config, wb_config):
        if hasattr(mod, name):
            setattr(mod, name, value)


def load_from_toml(path: str = "config.toml") -> None:
    """从 TOML 文件加载配置，覆盖默认值。文件不存在则静默跳过。"""
    if not os.path.isfile(path):
        return

    with open(path, "rb") as f:
        data = tomllib.load(f)

    for toml_key, config_var in _TOML_KEY_MAP.items():
        if toml_key not in data:
            continue
        value = data[toml_key]
        # keywords: list → 逗号拼接字符串
        if toml_key == "keywords" and isinstance(value, list):
            value = ",".join(str(v) for v in value)
        # note_ids / creator_ids: 自动从 URL 中提取数字 ID
        if toml_key in ("note_ids", "creator_ids") and isinstance(value, list):
            value = [_extract_weibo_id(str(v)) for v in value]
        _set(config_var, value)


def apply_cli_args(args) -> None:
    """从 CLI 参数覆盖配置（最高优先级）。args 为 argparse.Namespace。"""
    command = getattr(args, "command", None)
    if command:
        _set("CRAWLER_TYPE", command)

    # search 专属
    if command == "search":
        keywords = getattr(args, "keywords", None)
        if keywords:
            _set("KEYWORDS", ",".join(keywords))
        search_type = getattr(args, "search_type", None)
        if search_type is not None:
            _set("WEIBO_SEARCH_TYPE", search_type)

    # detail 专属
    if command == "detail":
        ids = getattr(args, "ids", None)
        if ids:
            _set("WEIBO_SPECIFIED_ID_LIST", [_extract_weibo_id(i) for i in ids])

    # creator 专属
    if command == "creator":
        ids = getattr(args, "ids", None)
        if ids:
            _set("WEIBO_CREATOR_ID_LIST", [_extract_weibo_id(i) for i in ids])

    # ---- 公共选项（仅覆盖 CLI 显式传入的值，None 表示未传入） ----
    _CLI_OPTION_MAP = {
        "output":           "SAVE_DATA_PATH",
        "format":           "SAVE_DATA_OPTION",
        "login":            "LOGIN_TYPE",
        "cookie":           "COOKIES",
        "count":            "CRAWLER_MAX_NOTES_COUNT",
        "comments_count":   "CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES",
        "sleep":            "CRAWLER_MAX_SLEEP_SEC",
    }
    for cli_attr, config_var in _CLI_OPTION_MAP.items():
        val = getattr(args, cli_attr, None)
        if val is not None:
            _set(config_var, val)

    # 布尔开关（store_true → True 表示用户显式传了）
    if getattr(args, "headless", None) is True:
        _set("HEADLESS", True)
        _set("CDP_HEADLESS", True)
    if getattr(args, "no_comments", None) is True:
        _set("ENABLE_GET_COMMENTS", False)
    if getattr(args, "with_media", None) is True:
        _set("ENABLE_GET_MEIDAS", True)
    if getattr(args, "with_sub_comments", None) is True:
        _set("ENABLE_GET_SUB_COMMENTS", True)
    if getattr(args, "with_wordcloud", None) is True:
        _set("ENABLE_GET_WORDCLOUD", True)
    if getattr(args, "full_text", None) is True:
        _set("ENABLE_WEIBO_FULL_TEXT", True)
    if getattr(args, "no_full_text", None) is True:
        _set("ENABLE_WEIBO_FULL_TEXT", False)
