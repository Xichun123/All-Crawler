# -*- coding: utf-8 -*-
# 小红书存储实现 (精简版 - 仅 CSV 和 JSON)

from typing import Dict

from base.base_crawler import AbstractStore
from tools.async_file_writer import AsyncFileWriter
from var import crawler_type_var


class XhsCsvStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="xhs"
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_to_csv(item=content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_to_csv(item=comment_item, item_type="comments")

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_to_csv(item=creator, item_type="creators")


class XhsJsonStoreImplement(AbstractStore):
    def __init__(self):
        self.file_writer = AsyncFileWriter(
            crawler_type=crawler_type_var.get(),
            platform="xhs"
        )

    async def store_content(self, content_item: Dict):
        await self.file_writer.write_single_item_to_json(item=content_item, item_type="contents")

    async def store_comment(self, comment_item: Dict):
        await self.file_writer.write_single_item_to_json(item=comment_item, item_type="comments")

    async def store_creator(self, creator: Dict):
        await self.file_writer.write_single_item_to_json(item=creator, item_type="creators")
