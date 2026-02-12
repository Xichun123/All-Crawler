# -*- coding: utf-8 -*-
# 整洁 JSON 输出模块 — 将原始 API 数据转换为中文字段名的 JSON 文件

import json
import os
from datetime import datetime
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


def _format_timestamp(ts: Any) -> str:
    """unix timestamp (毫秒) → 可读时间字符串"""
    try:
        v = int(ts)
        # 小红书的时间戳是毫秒级
        if v > 1e12:
            v = v // 1000
        return datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return str(ts) if ts else ""


def _output_dir() -> str:
    base = config.SAVE_DATA_PATH or "data"
    path = os.path.join(base, "xhs")
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
    user_info = comment_item.get("user_info", {})
    target_comment = comment_item.get("target_comment", {})
    parent_id = target_comment.get("id", "")
    result = {
        "评论ID": comment_item.get("id", ""),
        "评论内容": comment_item.get("content", ""),
        "评论者昵称": user_info.get("nickname", ""),
        "发布时间": _format_timestamp(comment_item.get("create_time")),
        "IP属地": comment_item.get("ip_location", ""),
        "点赞数": _safe_int(comment_item.get("like_count")),
    }
    if parent_id and str(parent_id) != "0":
        result["回复评论ID"] = str(parent_id)
    return result


def _map_note(note_item: Dict, comments: Optional[List[Dict]] = None) -> Dict:
    """从原始 note_item 提取笔记字段，映射为中文 key"""
    interact = note_item.get("interact_info", {})
    note_id = note_item.get("note_id", "")
    image_list = note_item.get("image_list", [])
    tag_list = note_item.get("tag_list", [])
    result = {
        "标题": note_item.get("title", "") or note_item.get("desc", "")[:100],
        "描述": note_item.get("desc", ""),
        "类型": note_item.get("type", ""),
        "发布时间": _format_timestamp(note_item.get("time")),
        "笔记链接": f"https://www.xiaohongshu.com/explore/{note_id}" if note_id else "",
        "点赞数": _safe_int(interact.get("liked_count")),
        "收藏数": _safe_int(interact.get("collected_count")),
        "评论数": _safe_int(interact.get("comment_count")),
        "分享数": _safe_int(interact.get("share_count")),
        "IP属地": note_item.get("ip_location", ""),
        "标签": [tag.get("name", "") for tag in tag_list if tag.get("type") == "topic"],
        "图片数": len(image_list),
    }
    if comments is not None:
        result["评论列表"] = [_map_comment(c) for c in comments]
    return result


def _map_note_with_author(note_item: Dict, comments: Optional[List[Dict]] = None) -> Dict:
    """笔记字段 + 作者昵称（用于 search / detail 模式）"""
    note = _map_note(note_item, comments)
    user = note_item.get("user", {})
    result = {"标题": note.pop("标题"), "作者昵称": user.get("nickname", "")}
    result.update(note)
    return result


def _map_creator(creator_raw: Dict) -> Dict:
    """从原始 creator API 响应提取作者信息"""
    user_info = creator_raw.get("basicInfo", {})

    follows = 0
    fans = 0
    interaction = 0
    for i in creator_raw.get("interactions", []):
        if i.get("type") == "follows":
            follows = i.get("count", 0)
        elif i.get("type") == "fans":
            fans = i.get("count", 0)
        elif i.get("type") == "interaction":
            interaction = i.get("count", 0)

    tags = creator_raw.get("tags", [])
    tag_info = {tag.get("tagType", ""): tag.get("name", "") for tag in tags} if tags else {}

    return {
        "昵称": user_info.get("nickname", ""),
        "简介": user_info.get("desc", ""),
        "IP属地": user_info.get("ipLocation", ""),
        "粉丝数": fans,
        "关注数": follows,
        "获赞与收藏": interaction,
        "标签": tag_info,
    }


def _write_json(data: Dict, filepath: str) -> str:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


# ---- 公开接口 ----

# comments_by_note: Dict[note_id, List[raw_comment_dict]]

def write_creator_result(
    creator_raw: Dict,
    notes_raw: List[Dict],
    comments_by_note: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """creator 模式：一个作者 + 其笔记列表"""
    author_info = _map_creator(creator_raw)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbn = comments_by_note or {}

    result = {
        "爬取时间": now,
        "爬取模式": "creator",
        "作者": author_info,
        "笔记列表": [
            _map_note(n, cbn.get(n.get("note_id", ""), None))
            for n in notes_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("creator", author_info.get("昵称", ""))
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] creator 数据已写入: {filepath} ({len(notes_raw)} 条笔记)")
    return filepath


def write_search_result(
    keyword: str,
    notes_raw: List[Dict],
    comments_by_note: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """search 模式：一个关键词 + 搜索到的笔记列表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbn = comments_by_note or {}

    result = {
        "爬取时间": now,
        "爬取模式": "search",
        "搜索关键词": keyword,
        "笔记列表": [
            _map_note_with_author(n, cbn.get(n.get("note_id", ""), None))
            for n in notes_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("search", keyword)
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] search 数据已写入: {filepath} ({len(notes_raw)} 条笔记)")
    return filepath


def write_detail_result(
    notes_raw: List[Dict],
    comments_by_note: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """detail 模式：指定笔记的详情列表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbn = comments_by_note or {}

    result = {
        "爬取时间": now,
        "爬取模式": "detail",
        "笔记列表": [
            _map_note_with_author(n, cbn.get(n.get("note_id", ""), None))
            for n in notes_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("detail", f"{len(notes_raw)}条笔记")
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] detail 数据已写入: {filepath} ({len(notes_raw)} 条笔记)")
    return filepath
