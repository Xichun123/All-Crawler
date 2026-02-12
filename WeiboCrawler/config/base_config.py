# -*- coding: utf-8 -*-
# 微博爬虫 - 基础配置 (从 MediaCrawler 精简而来，仅保留微博相关)

# 平台固定为微博
PLATFORM = "wb"

# 关键词搜索配置，以英文逗号分隔
KEYWORDS = "Python,编程"

# 登录方式: qrcode | phone | cookie
LOGIN_TYPE = "qrcode"
COOKIES = ""

# 爬取类型: search(关键词搜索) | detail(帖子详情) | creator(创作者主页数据)
CRAWLER_TYPE = "search"

# 是否开启 IP 代理
ENABLE_IP_PROXY = False

# 代理IP池数量
IP_PROXY_POOL_COUNT = 2

# 代理IP提供商名称: kuaidaili | wandouhttp
IP_PROXY_PROVIDER_NAME = "kuaidaili"

# 设置为True不会打开浏览器（无头浏览器）
HEADLESS = False

# 是否保存登录状态
SAVE_LOGIN_STATE = True

# ==================== CDP (Chrome DevTools Protocol) 配置 ====================
ENABLE_CDP_MODE = True
CDP_DEBUG_PORT = 9222
CUSTOM_BROWSER_PATH = ""
CDP_HEADLESS = False
BROWSER_LAUNCH_TIMEOUT = 60
AUTO_CLOSE_BROWSER = True

# 数据保存类型: csv | json
SAVE_DATA_OPTION = "json"

# 数据保存路径，默认不指定则保存到 data 文件夹下
SAVE_DATA_PATH = ""

# 用户浏览器缓存目录
USER_DATA_DIR = "%s_user_data_dir"

# 爬取开始页数
START_PAGE = 1

# 爬取视频/帖子的数量控制
CRAWLER_MAX_NOTES_COUNT = 20

# 并发爬虫数量控制
MAX_CONCURRENCY_NUM = 1

# 是否开启爬媒体模式（包含图片资源）
ENABLE_GET_MEIDAS = False

# 是否开启爬评论模式
ENABLE_GET_COMMENTS = True

# 爬取一级评论的数量控制(单帖子)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = 10

# 是否开启爬二级评论模式
ENABLE_GET_SUB_COMMENTS = False

# 词云相关
ENABLE_GET_WORDCLOUD = False
CUSTOM_WORDS = {
    "零几": "年份",
    "高频词": "专业术语",
}

# 停用词文件路径
STOP_WORDS_FILE = "./docs/hit_stopwords.txt"

# 中文字体文件路径
FONT_PATH = "./docs/STZHONGS.TTF"

# 爬取间隔时间（秒）
CRAWLER_MAX_SLEEP_SEC = 2

# 缓存类型
CACHE_TYPE_MEMORY = "memory"

# 导入微博专属配置 (会覆盖部分上面的默认值)
from .wb_config import *
