# -*- coding: utf-8 -*-
# 整洁 JSON 输出模块 — 将微博原始 API 数据转换为中文字段名的 JSON 文件

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import config
from tools import utils


def _safe_int(value: Any) -> int:
    """将各种类型安全转为 int"""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


def _format_rfc2822(rfc2822_time: Any) -> str:
    """RFC 2822 时间 → 可读时间字符串 (中国时区)"""
    if not rfc2822_time:
        return ""
    try:
        rfc2822_format = "%a %b %d %H:%M:%S %z %Y"
        dt_object = datetime.strptime(str(rfc2822_time), rfc2822_format)
        dt_china = dt_object.astimezone(timezone(timedelta(hours=8)))
        return dt_china.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return str(rfc2822_time)


def _clean_html(html_text: str) -> str:
    """去除 HTML 标签"""
    if not html_text:
        return ""
    return re.sub(r"<.*?>", "", html_text).strip()


def _output_dir() -> str:
    base = config.SAVE_DATA_PATH or "data"
    path = os.path.join(base, "weibo")
    os.makedirs(path, exist_ok=True)
    return path


def _gen_filename(mode: str, tag: str = "") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if tag:
        safe_tag = "".join(c for c in tag if c not in r'\/:*?"<>|')
        return f"{mode}_{safe_tag}_{ts}.json"
    return f"{mode}_{ts}.json"


def _map_comment(comment_item: Dict) -> Dict:
    """从原始评论 dict 提取字段，映射为中文 key"""
    user_info = comment_item.get("user", {}) or {}
    parent_id = comment_item.get("rootid", "")
    result = {
        "评论ID": str(comment_item.get("id", "")),
        "评论内容": _clean_html(comment_item.get("text", "")),
        "评论者昵称": user_info.get("screen_name", ""),
        "发布时间": _format_rfc2822(comment_item.get("created_at")),
        "IP属地": (comment_item.get("source", "") or "").replace("来自", ""),
        "点赞数": _safe_int(comment_item.get("like_count")),
    }
    if parent_id and str(parent_id) != str(comment_item.get("id", "")):
        result["回复评论ID"] = str(parent_id)
    return result


def _map_note(note_item: Dict, comments: Optional[List[Dict]] = None) -> Dict:
    """从原始 note_item (含 mblog) 提取帖子字段，映射为中文 key"""
    mblog = note_item.get("mblog", {}) or {}
    user_info = mblog.get("user", {}) or {}
    note_id = mblog.get("id", "")
    result = {
        "内容": _clean_html(mblog.get("text", "")),
        "发布时间": _format_rfc2822(mblog.get("created_at")),
        "微博链接": f"https://m.weibo.cn/detail/{note_id}",
        "点赞数": _safe_int(mblog.get("attitudes_count")),
        "评论数": _safe_int(mblog.get("comments_count")),
        "转发数": _safe_int(mblog.get("reposts_count")),
        "IP属地": (mblog.get("region_name", "") or "").replace("发布于 ", ""),
    }
    if comments is not None:
        result["评论列表"] = [_map_comment(c) for c in comments]
    return result


def _map_note_with_author(note_item: Dict, comments: Optional[List[Dict]] = None) -> Dict:
    """帖子字段 + 作者昵称（用于 search / detail 模式）"""
    note = _map_note(note_item, comments)
    mblog = note_item.get("mblog", {}) or {}
    user_info = mblog.get("user", {}) or {}
    # 将作者昵称插入到内容之前
    result = {"内容": note.pop("内容"), "作者昵称": user_info.get("screen_name", "")}
    result.update(note)
    return result


def _map_creator(user_info: Dict) -> Dict:
    """从原始 creator API 响应提取作者信息"""
    gender_map = {"m": "男", "f": "女"}
    return {
        "昵称": user_info.get("screen_name", ""),
        "简介": user_info.get("description", ""),
        "性别": gender_map.get(user_info.get("gender", ""), "未知"),
        "IP属地": (user_info.get("source", "") or "").replace("来自", ""),
        "粉丝数": _safe_int(user_info.get("followers_count")),
        "关注数": _safe_int(user_info.get("follow_count")),
        "微博数": _safe_int(user_info.get("statuses_count")),
        "user_id": str(user_info.get("id", "")),
        "主页链接": f"https://m.weibo.cn/u/{user_info.get('id', '')}",
    }


def _write_json(data: Dict, filepath: str) -> str:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


# ---- 公开接口 ----

# comments_by_note: Dict[note_id, List[raw_comment_dict]]

def write_creator_result(
    user_info: Dict,
    notes_raw: List[Dict],
    comments_by_note: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """creator 模式：一个作者 + 其帖子列表"""
    author_info = _map_creator(user_info)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbn = comments_by_note or {}

    result = {
        "爬取时间": now,
        "爬取模式": "creator",
        "作者": author_info,
        "微博列表": [
            _map_note(n, cbn.get(
                (n.get("mblog", {}) or {}).get("id", ""), None
            ))
            for n in notes_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("creator", author_info.get("昵称", ""))
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] creator 数据已写入: {filepath} ({len(notes_raw)} 条微博)")
    return filepath


def write_search_result(
    keyword: str,
    notes_raw: List[Dict],
    comments_by_note: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """search 模式：一个关键词 + 搜索到的帖子列表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbn = comments_by_note or {}

    result = {
        "爬取时间": now,
        "爬取模式": "search",
        "搜索关键词": keyword,
        "微博列表": [
            _map_note_with_author(n, cbn.get(
                (n.get("mblog", {}) or {}).get("id", ""), None
            ))
            for n in notes_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("search", keyword)
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] search 数据已写入: {filepath} ({len(notes_raw)} 条微博)")
    return filepath


def write_detail_result(
    notes_raw: List[Dict],
    comments_by_note: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """detail 模式：指定帖子的详情列表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbn = comments_by_note or {}

    result = {
        "爬取时间": now,
        "爬取模式": "detail",
        "微博列表": [
            _map_note_with_author(n, cbn.get(
                (n.get("mblog", {}) or {}).get("id", ""), None
            ))
            for n in notes_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("detail", f"{len(notes_raw)}条微博")
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] detail 数据已写入: {filepath} ({len(notes_raw)} 条微博)")
    return filepath
