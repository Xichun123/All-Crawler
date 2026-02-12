# -*- coding: utf-8 -*-
# 小红书媒体存储 (图片/视频下载保存)

import pathlib
from typing import Dict

import aiofiles

from base.base_crawler import AbstractStoreImage, AbstractStoreVideo
from tools import utils
import config


class XiaoHongShuImage(AbstractStoreImage):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.image_store_path = f"{config.SAVE_DATA_PATH}/xhs/images"
        else:
            self.image_store_path = "data/xhs/images"

    async def store_image(self, image_content_item: Dict):
        await self.save_image(image_content_item.get("notice_id"), image_content_item.get("pic_content"), image_content_item.get("extension_file_name"))

    def make_save_file_name(self, notice_id: str, extension_file_name: str) -> str:
        return f"{self.image_store_path}/{notice_id}/{extension_file_name}"

    async def save_image(self, notice_id: str, pic_content: str, extension_file_name):
        pathlib.Path(self.image_store_path + "/" + notice_id).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(notice_id, extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(pic_content)
            utils.logger.info(f"[XiaoHongShuImage.save_image] save image {save_file_name} success ...")


class XiaoHongShuVideo(AbstractStoreVideo):
    def __init__(self):
        if config.SAVE_DATA_PATH:
            self.video_store_path = f"{config.SAVE_DATA_PATH}/xhs/videos"
        else:
            self.video_store_path = "data/xhs/videos"

    async def store_video(self, video_content_item: Dict):
        await self.save_video(video_content_item.get("notice_id"), video_content_item.get("video_content"), video_content_item.get("extension_file_name"))

    def make_save_file_name(self, notice_id: str, extension_file_name: str) -> str:
        return f"{self.video_store_path}/{notice_id}/{extension_file_name}"

    async def save_video(self, notice_id: str, video_content: str, extension_file_name):
        pathlib.Path(self.video_store_path + "/" + notice_id).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(notice_id, extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(video_content)
            utils.logger.info(f"[XiaoHongShuVideo.save_video] save video {save_file_name} success ...")
