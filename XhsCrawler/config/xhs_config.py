# -*- coding: utf-8 -*-
# 小红书平台配置

# 排序方式，具体的枚举值在 media_platform/xhs/field.py 中
# general(综合排序) | popularity_descending(最热排序) | time_descending(最新排序)
SORT_TYPE = "general"

# 指定笔记URL列表，必须要携带 xsec_token 参数
# 支持格式:
# 1. 完整URL: "https://www.xiaohongshu.com/explore/64b95d01000000000c034587?xsec_token=xxx&xsec_source=pc_cfeed"
XHS_SPECIFIED_NOTE_URL_LIST: list[str] = [
    # 通过 config.toml 或 CLI 参数指定，例如:
    #   python main.py detail "https://www.xiaohongshu.com/explore/xxx?xsec_token=xxx"
]

# 指定创作者URL列表，需要携带 xsec_token 和 xsec_source 参数
# 支持格式:
# 1. 完整URL: "https://www.xiaohongshu.com/user/profile/xxx?xsec_token=xxx&xsec_source=pc_search"
XHS_CREATOR_ID_LIST: list[str] = [
    # 通过 config.toml 或 CLI 参数指定，例如:
    #   python main.py creator "https://www.xiaohongshu.com/user/profile/xxx?xsec_token=xxx"
]

CRAWLER_MAX_NOTES_COUNT = 20
