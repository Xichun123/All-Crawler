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
    """unix timestamp → 可读时间字符串"""
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return ""


def _output_dir() -> str:
    base = config.SAVE_DATA_PATH or "data"
    path = os.path.join(base, "douyin")
    os.makedirs(path, exist_ok=True)
    return path


def _gen_filename(mode: str, tag: str = "") -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if tag:
        # 文件名安全化：去除路径分隔符等特殊字符
        safe_tag = "".join(c for c in tag if c not in r'\/:*?"<>|')
        return f"{mode}_{safe_tag}_{ts}.json"
    return f"{mode}_{ts}.json"


def _map_comment(comment_item: Dict) -> Dict:
    """从原始评论 dict 提取字段，映射为中文 key"""
    user_info = comment_item.get("user", {})
    parent_id = comment_item.get("reply_id", "0")
    result = {
        "评论ID": comment_item.get("cid", ""),
        "评论内容": comment_item.get("text", ""),
        "评论者昵称": user_info.get("nickname", ""),
        "发布时间": _format_timestamp(comment_item.get("create_time")),
        "IP属地": comment_item.get("ip_label", ""),
        "点赞数": _safe_int(comment_item.get("digg_count")),
    }
    if parent_id and parent_id != "0":
        result["回复评论ID"] = parent_id
    return result


def _map_video(aweme_item: Dict, comments: Optional[List[Dict]] = None) -> Dict:
    """从原始 aweme_item 提取视频字段，映射为中文 key"""
    interact = aweme_item.get("statistics", {})
    aweme_id = aweme_item.get("aweme_id", "")
    result = {
        "标题": aweme_item.get("desc", ""),
        "发布时间": _format_timestamp(aweme_item.get("create_time")),
        "视频链接": f"https://www.douyin.com/video/{aweme_id}",
        "点赞数": _safe_int(interact.get("digg_count")),
        "收藏数": _safe_int(interact.get("collect_count")),
        "评论数": _safe_int(interact.get("comment_count")),
        "分享数": _safe_int(interact.get("share_count")),
    }
    if comments is not None:
        result["评论列表"] = [_map_comment(c) for c in comments]
    return result


def _map_video_with_author(aweme_item: Dict, comments: Optional[List[Dict]] = None) -> Dict:
    """视频字段 + 作者昵称（用于 search / detail 模式）"""
    video = _map_video(aweme_item, comments)
    author = aweme_item.get("author", {})
    # 插入到标题之后
    result = {"标题": video.pop("标题"), "作者昵称": author.get("nickname", "")}
    result.update(video)
    return result


def _map_creator(creator_raw: Dict) -> Dict:
    """从原始 creator API 响应提取作者信息"""
    user = creator_raw.get("user", {})
    sec_uid = user.get("sec_uid", "")
    return {
        "昵称": user.get("nickname", ""),
        "抖音号": user.get("unique_id", "") or user.get("short_id", ""),
        "简介": user.get("signature", ""),
        "IP属地": user.get("ip_location", ""),
        "粉丝数": _safe_int(user.get("max_follower_count")),
        "关注数": _safe_int(user.get("following_count")),
        "获赞总数": _safe_int(user.get("total_favorited")),
        "作品数": _safe_int(user.get("aweme_count")),
        "user_id": user.get("uid", ""),
        "sec_uid": sec_uid,
        "主页链接": f"https://www.douyin.com/user/{sec_uid}" if sec_uid else "",
    }


def _write_json(data: Dict, filepath: str) -> str:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


# ---- 公开接口 ----

# comments_by_aweme: Dict[aweme_id, List[raw_comment_dict]]

def write_creator_result(
    creator_raw: Dict,
    videos_raw: List[Dict],
    comments_by_aweme: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """creator 模式：一个作者 + 其视频列表"""
    author_info = _map_creator(creator_raw)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cba = comments_by_aweme or {}

    result = {
        "爬取时间": now,
        "爬取模式": "creator",
        "作者": author_info,
        "视频列表": [
            _map_video(v, cba.get(v.get("aweme_id", ""), None))
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
    comments_by_aweme: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """search 模式：一个关键词 + 搜索到的视频列表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cba = comments_by_aweme or {}

    result = {
        "爬取时间": now,
        "爬取模式": "search",
        "搜索关键词": keyword,
        "视频列表": [
            _map_video_with_author(v, cba.get(v.get("aweme_id", ""), None))
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
    comments_by_aweme: Optional[Dict[str, List[Dict]]] = None,
    output_dir: Optional[str] = None,
) -> str:
    """detail 模式：指定视频的详情列表"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cba = comments_by_aweme or {}

    result = {
        "爬取时间": now,
        "爬取模式": "detail",
        "视频列表": [
            _map_video_with_author(v, cba.get(v.get("aweme_id", ""), None))
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
