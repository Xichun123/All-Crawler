# -*- coding: utf-8 -*-
# 微博爬虫 - 微博平台专属配置

# 搜索类型: default | real_time | popular | video
WEIBO_SEARCH_TYPE = "default"

# 指定微博ID列表 (detail 模式)
# 通过 config.toml 或 CLI 参数指定，例如:
#   python main.py detail "4982041758140155"
WEIBO_SPECIFIED_ID_LIST: list[str] = [
]

# 指定微博用户ID列表 (creator 模式)
# 通过 config.toml 或 CLI 参数指定，例如:
#   python main.py creator "5756404150"
WEIBO_CREATOR_ID_LIST: list[str] = [
]

# 是否开启微博爬取全文的功能，默认开启
# 如果开启的话会增加被风控的概率
ENABLE_WEIBO_FULL_TEXT = True

CRAWLER_MAX_NOTES_COUNT = 20
