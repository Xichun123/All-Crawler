# -*- coding: utf-8 -*-
# 微博数据存储 (精简版 - 仅支持 CSV 和 JSON)

import re
from typing import Dict, List

import config
from tools import utils
from var import source_keyword_var

from ._store_impl import *
from .weibo_store_media import *


class WeibostoreFactory:
    STORES = {
        "csv": WeiboCsvStoreImplement,
        "json": WeiboJsonStoreImplement,
    }

    @staticmethod
    def create_store() -> "AbstractStore":
        from base.base_crawler import AbstractStore
        store_class = WeibostoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not store_class:
            raise ValueError(
                f"[WeibostoreFactory.create_store] Invalid save option: {config.SAVE_DATA_OPTION}. "
                f"Only supported: {', '.join(WeibostoreFactory.STORES.keys())}"
            )
        return store_class()


async def batch_update_weibo_notes(note_list: List[Dict]):
    if not note_list:
        return
    for note_item in note_list:
        await update_weibo_note(note_item)


async def update_weibo_note(note_item: Dict):
    if not note_item:
        return

    mblog: Dict = note_item.get("mblog")
    user_info: Dict = mblog.get("user")
    note_id = mblog.get("id")
    content_text = mblog.get("text")
    clean_text = re.sub(r"<.*?>", "", content_text)
    save_content_item = {
        # 微博信息
        "note_id": note_id,
        "content": clean_text,
        "create_time": utils.rfc2822_to_timestamp(mblog.get("created_at")),
        "create_date_time": str(utils.rfc2822_to_china_datetime(mblog.get("created_at"))),
        "liked_count": str(mblog.get("attitudes_count", 0)),
        "comments_count": str(mblog.get("comments_count", 0)),
        "shared_count": str(mblog.get("reposts_count", 0)),
        "last_modify_ts": utils.get_current_timestamp(),
        "note_url": f"https://m.weibo.cn/detail/{note_id}",
        "ip_location": mblog.get("region_name", "").replace("发布于 ", ""),

        # 用户信息
        "user_id": str(user_info.get("id")),
        "nickname": user_info.get("screen_name", ""),
        "gender": user_info.get("gender", ""),
        "profile_url": user_info.get("profile_url", ""),
        "avatar": user_info.get("profile_image_url", ""),
        "source_keyword": source_keyword_var.get(),
    }
    utils.logger.info(f"[store.weibo.update_weibo_note] weibo note id:{note_id}, title:{save_content_item.get('content')[:24]} ...")
    await WeibostoreFactory.create_store().store_content(content_item=save_content_item)


async def batch_update_weibo_note_comments(note_id: str, comments: List[Dict]):
    if not comments:
        return
    for comment_item in comments:
        await update_weibo_note_comment(note_id, comment_item)


async def update_weibo_note_comment(note_id: str, comment_item: Dict):
    if not comment_item or not note_id:
        return
    comment_id = str(comment_item.get("id"))
    user_info: Dict = comment_item.get("user")
    content_text = comment_item.get("text")
    clean_text = re.sub(r"<.*?>", "", content_text)
    save_comment_item = {
        "comment_id": comment_id,
        "create_time": utils.rfc2822_to_timestamp(comment_item.get("created_at")),
        "create_date_time": str(utils.rfc2822_to_china_datetime(comment_item.get("created_at"))),
        "note_id": note_id,
        "content": clean_text,
        "sub_comment_count": str(comment_item.get("total_number", 0)),
        "comment_like_count": str(comment_item.get("like_count", 0)),
        "last_modify_ts": utils.get_current_timestamp(),
        "ip_location": comment_item.get("source", "").replace("来自", ""),
        "parent_comment_id": comment_item.get("rootid", ""),

        # 用户信息
        "user_id": str(user_info.get("id")),
        "nickname": user_info.get("screen_name", ""),
        "gender": user_info.get("gender", ""),
        "profile_url": user_info.get("profile_url", ""),
        "avatar": user_info.get("profile_image_url", ""),
    }
    utils.logger.info(f"[store.weibo.update_weibo_note_comment] Weibo note comment: {comment_id}, content: {save_comment_item.get('content', '')[:24]} ...")
    await WeibostoreFactory.create_store().store_comment(comment_item=save_comment_item)


async def update_weibo_note_image(picid: str, pic_content, extension_file_name):
    await WeiboStoreImage().store_image({"pic_id": picid, "pic_content": pic_content, "extension_file_name": extension_file_name})


async def save_creator(user_id: str, user_info: Dict):
    local_db_item = {
        'user_id': user_id,
        'nickname': user_info.get('screen_name'),
        'gender': 'Female' if user_info.get('gender') == "f" else 'Male',
        'avatar': user_info.get('avatar_hd'),
        'desc': user_info.get('description'),
        'ip_location': user_info.get("source", "").replace("来自", ""),
        'follows': user_info.get('follow_count', ''),
        'fans': user_info.get('followers_count', ''),
        'tag_list': '',
        "last_modify_ts": utils.get_current_timestamp(),
    }
    utils.logger.info(f"[store.weibo.save_creator] creator:{local_db_item}")
    await WeibostoreFactory.create_store().store_creator(local_db_item)
