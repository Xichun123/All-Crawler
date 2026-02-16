# All Crawler
## 📦 包含的爬虫

- **BilibiliCrawler** - B站爬虫
- **DouyinCrawler** - 抖音爬虫
- **XhsCrawler** - 小红书爬虫
- **KuaishouCrawler** - 快手爬虫
- **WeiboCrawler** - 微博爬虫

## ✨ 主要特性

- 🔐 多种登录方式（扫码登录 / Cookie）
- 📊 多种数据格式（JSON / CSV）
- 💬 评论爬取（支持多级评论）
- 🖼️ 媒体下载（视频/图片）
- ☁️ 词云生成
- 🛡️ 防封禁机制（随机延迟、User-Agent 轮换）
- 🎯 多种爬取模式（搜索/详情/创作者）

## 📋 环境要求

- Python >= 3.11
- 操作系统：Windows / macOS / Linux

## 🚀 快速开始

### 1. BilibiliCrawler（简单版）

B站爬虫使用简单的 requests 库，无需安装浏览器驱动。

```bash
cd BilibiliCrawler

# 爬取UP主视频数据
python bilibili_scraper.py

# 爬取视频评论
python bilibili_comments_scraper.py
```

**使用说明：**
- 运行脚本后，按提示输入UP主主页链接或视频链接
- 数据自动保存为 CSV 文件
- 包含防封禁保护（随机延迟、请求限流）

### 2. DouyinCrawler / XhsCrawler / KuaishouCrawler / WeiboCrawler

这些爬虫基于 Playwright 浏览器自动化，功能更强大。

#### 安装依赖

```bash
# 以抖音爬虫为例
cd DouyinCrawler

# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

#### 配置爬虫

编辑 `config.toml` 文件：

```toml
# 爬取模式: search / detail / creator
mode = "detail"

# 搜索关键词（search 模式）
keywords = ["美食"]

# 视频链接（detail 模式）
video_urls = ["https://www.douyin.com/video/7525538910311632128"]

# 创作者链接（creator 模式）
creator_urls = ["https://www.douyin.com/user/MS4wLjABAAAA..."]

# 登录方式: qrcode / cookie
login = "qrcode"

# 数据保存格式: json / csv
format = "json"

# 爬取数量
count = 20
comments_count = 10

# 功能开关
comments = true        # 是否爬取评论
sub_comments = false   # 是否爬取二级评论
media = false          # 是否下载视频/图片
wordcloud = false      # 是否生成词云
```

#### 运行爬虫

```bash
# 使用配置文件运行
python main.py

# 或使用命令行参数（覆盖配置文件）
python main.py search "美食"
python main.py detail "https://www.douyin.com/video/..."
python main.py creator "https://www.douyin.com/user/..."

# 查看帮助
python main.py --help
```

## 📁 项目结构

```
All Crawler/
├── BilibiliCrawler/          # B站爬虫（简单版）
│   ├── bilibili_scraper.py           # UP主视频数据爬虫
│   ├── bilibili_comments_scraper.py  # 视频评论爬虫
│   └── bilibili_data/                # 输出目录
│
├── DouyinCrawler/            # 抖音爬虫
│   ├── main.py              # 主入口
│   ├── cli.py               # 命令行接口
│   ├── config.toml          # 配置文件
│   └── pyproject.toml       # 项目依赖
│
├── XhsCrawler/              # 小红书爬虫
├── KuaishouCrawler/         # 快手爬虫
└── WeiboCrawler/            # 微博爬虫
```

## 🔧 爬取模式说明

### 1. 搜索模式（search）
根据关键词搜索内容并爬取

```bash
python main.py search "关键词"
```

### 2. 详情模式（detail）
爬取指定视频/帖子的详细信息和评论

```bash
python main.py detail "视频链接"
```

### 3. 创作者模式（creator）
爬取指定创作者的所有作品

```bash
python main.py creator "创作者主页链接"
```

## 📊 数据输出

### CSV 格式
- 适合数据分析和 Excel 查看
- 每个UP主/视频单独保存一个文件
- 自动处理中文编码

### JSON 格式
- 保留完整的数据结构
- 适合程序化处理
- 支持词云生成

## ⚠️ 注意事项

1. **仅供学习研究使用**，请遵守各平台的使用条款和 robots.txt
2. **请勿用于商业用途**或大规模数据采集
3. **合理控制爬取频率**，避免对平台服务器造成压力
4. **尊重用户隐私**，不要爬取和传播敏感信息
5. 首次运行需要扫码登录或配置 Cookie
6. 建议使用代理 IP 以避免账号被封禁

## 🛡️ 防封禁机制

- ✅ 随机请求延迟
- ✅ User-Agent 轮换
- ✅ 请求限流和批次休息
- ✅ 自动重试机制
- ✅ Cookie 管理

## 🐛 常见问题

**Q: 为什么需要登录？**
A: 大部分平台需要登录才能访问完整数据，建议使用扫码登录方式。

**Q: 爬虫运行很慢？**
A: 这是正常的，防封禁机制会添加随机延迟。可以适当调整 `config.toml` 中的 `sleep` 参数。

**Q: 提示"需要安装 Playwright 浏览器"？**
A: 运行 `playwright install chromium` 安装浏览器驱动。

**Q: BilibiliCrawler 和其他爬虫有什么区别？**
A: BilibiliCrawler 是轻量级版本，使用 requests 库，无需浏览器；其他爬虫使用 Playwright，功能更强大但需要安装浏览器驱动。

## 📝 许可证

本项目仅供学习和研究使用。使用本项目时，请遵守相关法律法规和平台使用条款。

## 🙏 致谢

- DouyinCrawler、XhsCrawler、KuaishouCrawler、WeiboCrawler 基于 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 项目移植
- 感谢所有开源贡献者

## 📧 联系方式

如有问题或建议，欢迎提交 Issue。
