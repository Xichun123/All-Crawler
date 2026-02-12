# -*- coding: utf-8 -*-
# 快手平台配置

PUBLISH_TIME_TYPE = 0

# 指定快手视频URL列表 (支持多种格式)
# 支持格式:
# 1. 完整视频URL: "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs"
# 2. 纯视频ID: "3x3zxz4mjrsc8ke"
KS_SPECIFIED_ID_LIST: list[str] = [
    # 通过 config.toml 或 CLI 参数指定，例如:
    #   python main.py detail "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke"
]

# 指定快手创作者URL列表 (支持完整URL或user_id)
# 支持格式:
# 1. 完整创作者主页URL: "https://www.kuaishou.com/profile/3x84qugg4ch9zhs"
# 2. user_id: "3x84qugg4ch9zhs"
KS_CREATOR_ID_LIST: list[str] = [
    # 通过 config.toml 或 CLI 参数指定，例如:
    #   python main.py creator "https://www.kuaishou.com/profile/3x84qugg4ch9zhs"
]
CRAWLER_MAX_NOTES_COUNT = 20
