# -*- coding: utf-8 -*-
# 整洁 JSON 输出模块 — 将快手原始 API 数据转换为中文字段名的 JSON 文件

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import config
from tools import utils


def _safe_int(value: Any) -> int:
    """将各种类型安全转为 int，支持中文数字格式（如 '89.1万'、'1.2亿'）"""
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        pass
    # 处理中文数字格式
    try:
        s = str(value).replace(",", "").strip()
        if "亿" in s:
            return int(float(s.replace("亿", "")) * 100000000)
        if "万" in s:
            return int(float(s.replace("万", "")) * 10000)
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def _format_timestamp(ts: Any) -> str:
    """unix timestamp (毫秒或秒) → 可读时间字符串"""
    try:
        ts_int = int(ts)
        if ts_int > 1e12:
            ts_int = ts_int // 1000
        return datetime.fromtimestamp(ts_int).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return ""


def _output_dir() -> str:
    base = config.SAVE_DATA_PATH or "data"
    path = os.path.join(base, "kuaishou")
    os.makedirs(path, exist_ok=True)
    return path


def _gen_filename(mode: str, tag: str = "") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if tag:
        safe_tag = "".join(c for c in tag if c not in r'\/:*?"<>|')
        return f"{mode}_{safe_tag}_{ts}.json"
    return f"{mode}_{ts}.json"


def _map_comment(comment_item: Dict) -> Dict:
    """从原始评论 dict 提取字段，映射为中文 key
    快手 V2 API 使用 snake_case，旧 GraphQL API 使用 camelCase，兼容两种
    """
    comment_id = comment_item.get("comment_id") or comment_item.get("commentId", "")
    author_name = comment_item.get("author_name") or comment_item.get("authorName", "")
    sub_count = comment_item.get("commentCount") or comment_item.get("subCommentCount", 0)
    result = {
        "评论ID": str(comment_id),
        "评论内容": comment_item.get("content", ""),
        "评论者昵称": author_name,
        "发布时间": _format_timestamp(comment_item.get("timestamp")),
        "子评论数": _safe_int(sub_count),
    }
    return result


def _map_video(video_item: Dict, comments: Optional[List[Dict]] = None) -> Dict:
    """从原始 video_item 提取视频字段，映射为中文 key
    快手 API 结构: video_item.photo 存视频信息, video_item.author 存作者信息
    """
    photo = video_item.get("photo", {}) or {}
    video_id = photo.get("id", "")
    result = {
        "标题": photo.get("caption", ""),
        "发布时间": _format_timestamp(photo.get("timestamp")),
        "视频链接": f"https://www.kuaishou.com/short-video/{video_id}",
        "点赞数": _safe_int(photo.get("realLikeCount")),
        "观看数": _safe_int(photo.get("viewCount")),
    }
    if comments is not None:
        result["评论列表"] = [_map_comment(c) for c in comments]
    return result


def _map_video_with_author(video_item: Dict, comments: Optional[List[Dict]] = None) -> Dict:
    """视频字段 + 作者昵称（用于 search / detail 模式）"""
    video = _map_video(video_item, comments)
    author = video_item.get("author", {}) or {}
    result = {"标题": video.pop("标题"), "作者昵称": author.get("name", "")}
    result.update(video)
    return result


def _map_creator(creator_raw: Dict) -> Dict:
    """从原始 creator API 响应提取作者信息
    快手 creator 结构: creator_raw.profile + creator_raw.ownerCount
    """
    profile = creator_raw.get("profile", {}) or {}
    owner_count = creator_raw.get("ownerCount", {}) or {}
    user_id = profile.get("user_id") or creator_raw.get("user_id", "")
    gender_map = {"F": "女", "M": "男"}
    return {
        "昵称": profile.get("user_name", ""),
        "简介": profile.get("user_text", ""),
        "性别": gender_map.get(profile.get("gender", ""), "未知"),
        "粉丝数": _safe_int(owner_count.get("fan")),
        "关注数": _safe_int(owner_count.get("follow")),
        "作品数": _safe_int(owner_count.get("photo_public")),
        "user_id": str(user_id),
        "主页链接": f"https://www.kuaishou.com/profile/{user_id}" if user_id else "",
    }


def _write_json(data: Dict, filepath: str) -> str:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


# ---- 公开接口 ----

# comments_by_video: Dict[video_id, List[raw_comment_dict]]

def write_creator_result(
    creator_raw: Dict,
    videos_raw: List[Dict],
    comments_by_video: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """creator 模式：一个作者 + 其视频列表"""
    author_info = _map_creator(creator_raw)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbv = comments_by_video or {}

    result = {
        "爬取时间": now,
        "爬取模式": "creator",
        "作者": author_info,
        "视频列表": [
            _map_video(v, cbv.get(
                (v.get("photo", {}) or {}).get("id", ""), None
            ))
            for v in videos_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("creator", author_info.get("昵称", ""))
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] creator 数据已写入: {filepath} ({len(videos_raw)} 条视频)")
    return filepath


def write_search_result(
    keyword: str,
    videos_raw: List[Dict],
    comments_by_video: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """search 模式：一个关键词 + 搜索到的视频列表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbv = comments_by_video or {}

    result = {
        "爬取时间": now,
        "爬取模式": "search",
        "搜索关键词": keyword,
        "视频列表": [
            _map_video_with_author(v, cbv.get(
                (v.get("photo", {}) or {}).get("id", ""), None
            ))
            for v in videos_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("search", keyword)
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] search 数据已写入: {filepath} ({len(videos_raw)} 条视频)")
    return filepath


def write_detail_result(
    videos_raw: List[Dict],
    comments_by_video: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """detail 模式：指定视频的详情列表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cbv = comments_by_video or {}

    result = {
        "爬取时间": now,
        "爬取模式": "detail",
        "视频列表": [
            _map_video_with_author(v, cbv.get(
                (v.get("photo", {}) or {}).get("id", ""), None
            ))
            for v in videos_raw
        ],
    }

    out = output_dir or _output_dir()
    os.makedirs(out, exist_ok=True)
    filename = _gen_filename("detail", f"{len(videos_raw)}条视频")
    filepath = os.path.join(out, filename)
    _write_json(result, filepath)
    utils.logger.info(f"[clean_writer] detail 数据已写入: {filepath} ({len(videos_raw)} 条视频)")
    return filepath
