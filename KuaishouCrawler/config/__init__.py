# -*- coding: utf-8 -*-
from .base_config import *

import os
import tomllib


# TOML key → config module variable 映射
_TOML_KEY_MAP = {
    "mode":              "CRAWLER_TYPE",
    "keywords":          "KEYWORDS",           # list → 逗号拼接字符串
    "video_urls":        "KS_SPECIFIED_ID_LIST",
    "creator_urls":      "KS_CREATOR_ID_LIST",
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
    "publish_time_type": "PUBLISH_TIME_TYPE",
}

_TIME_FILTER_MAP = {
    "all":       0,
    "day":       1,
    "week":      7,
    "half-year": 182,
}


def _set(name: str, value: object) -> None:
    """设置当前模块级变量"""
    globals()[name] = value
    # 同步到 base_config / ks_config，使 from config.xxx import YYY 也能拿到新值
    from . import base_config, ks_config
    for mod in (base_config, ks_config):
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
        time_filter = getattr(args, "time_filter", None)
        if time_filter is not None:
            _set("PUBLISH_TIME_TYPE", _TIME_FILTER_MAP.get(time_filter, 0))

    # detail 专属
    if command == "detail":
        urls = getattr(args, "urls", None)
        if urls:
            _set("KS_SPECIFIED_ID_LIST", list(urls))

    # creator 专属
    if command == "creator":
        urls = getattr(args, "urls", None)
        if urls:
            _set("KS_CREATOR_ID_LIST", list(urls))

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
