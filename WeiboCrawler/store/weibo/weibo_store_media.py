# -*- coding: utf-8 -*-
# 微博图片存储

import pathlib
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage
from tools import utils
import config


class WeiboStoreImage(AbstractStoreImage):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.image_store_path = f"{config.SAVE_DATA_PATH}/weibo/images"
        else:
            self.image_store_path = "data/weibo/images"

    async def store_image(self, image_content_item: Dict):
        await self.save_image(
            image_content_item.get("pic_id"),
            image_content_item.get("pic_content"),
            image_content_item.get("extension_file_name")
        )

    def make_save_file_name(self, picid: str, extension_file_name: str) -> str:
        return f"{self.image_store_path}/{picid}.{extension_file_name}"

    async def save_image(self, picid: str, pic_content: str, extension_file_name="jpg"):
        pathlib.Path(self.image_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(picid, extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(pic_content)
            utils.logger.info(f"[WeiboStoreImage.save_image] save image {save_file_name} success ...")
