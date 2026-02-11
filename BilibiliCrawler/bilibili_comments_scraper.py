"""
B站视频评论爬虫
支持输入多个视频链接，爬取评论数据
每个视频的评论单独保存为CSV文件
包含防封禁保护机制
"""

import requests
import csv
import os
import time
import re
import math
import random
from datetime import datetime


# 输出目录
OUTPUT_DIR = "bilibili_comments"

# ============== 防封禁配置 ==============
# 请求间隔（秒）- 随机范围
REQUEST_DELAY_MIN = 0.5
REQUEST_DELAY_MAX = 1.5

# 分页请求间隔
PAGE_DELAY_MIN = 1.0
PAGE_DELAY_MAX = 2.0

# 视频之间的间隔
VIDEO_DELAY_MIN = 3.0
VIDEO_DELAY_MAX = 6.0

# 连续请求多少次后休息
BATCH_SIZE = 30
BATCH_REST_MIN = 5.0
BATCH_REST_MAX = 10.0

# 请求重试配置
MAX_RETRIES = 3
RETRY_DELAY_MIN = 2.0
RETRY_DELAY_MAX = 5.0

# User-Agent 池
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# 请求计数器（用于批量休息）
request_counter = 0

# 全局SESSDATA变量
SESSDATA = None


def _optional_sessdata_cookie():
    global SESSDATA
    if not SESSDATA:
        return None
    return f"SESSDATA={SESSDATA}"


def _random_delay(min_delay, max_delay):
    """随机延迟"""
    delay = random.uniform(min_delay, max_delay)
    time.sleep(delay)


def _get_random_ua():
    """随机获取User-Agent"""
    return random.choice(USER_AGENTS)


def _check_batch_rest():
    """检查是否需要批量休息"""
    global request_counter
    request_counter += 1
    if request_counter >= BATCH_SIZE:
        request_counter = 0
        rest_time = random.uniform(BATCH_REST_MIN, BATCH_REST_MAX)
        print(f"    [防封禁] 已请求{BATCH_SIZE}次，休息{rest_time:.1f}秒...")
        time.sleep(rest_time)


def _safe_request(method, url, headers, params=None, retries=MAX_RETRIES):
    """
    安全请求封装，包含重试机制和错误处理
    """
    _check_batch_rest()

    for attempt in range(retries):
        try:
            # 每次请求使用随机UA
            headers = headers.copy()
            headers["User-Agent"] = _get_random_ua()

            response = requests.request(method, url, headers=headers, params=params, timeout=15)

            # 检查是否被风控
            if response.status_code == 412:
                print(f"    [警告] 触发风控(412)，等待后重试...")
                _random_delay(RETRY_DELAY_MIN * 2, RETRY_DELAY_MAX * 2)
                continue

            if response.status_code == 429:
                print(f"    [警告] 请求过快(429)，等待后重试...")
                _random_delay(RETRY_DELAY_MIN * 3, RETRY_DELAY_MAX * 3)
                continue

            response.raise_for_status()
            data = response.json()

            # 检查B站API错误码
            if data.get("code") == -412:
                print(f"    [警告] API风控(-412)，等待后重试...")
                _random_delay(RETRY_DELAY_MIN * 2, RETRY_DELAY_MAX * 2)
                continue

            if data.get("code") == -509:
                print(f"    [警告] 请求过于频繁(-509)，等待后重试...")
                _random_delay(RETRY_DELAY_MIN * 3, RETRY_DELAY_MAX * 3)
                continue

            return response

        except requests.exceptions.Timeout:
            print(f"    [警告] 请求超时，重试 {attempt + 1}/{retries}")
            _random_delay(RETRY_DELAY_MIN, RETRY_DELAY_MAX)
        except requests.exceptions.ConnectionError:
            print(f"    [警告] 连接错误，重试 {attempt + 1}/{retries}")
            _random_delay(RETRY_DELAY_MIN, RETRY_DELAY_MAX)
        except requests.RequestException as e:
            if attempt < retries - 1:
                print(f"    [警告] 请求异常: {e}，重试 {attempt + 1}/{retries}")
                _random_delay(RETRY_DELAY_MIN, RETRY_DELAY_MAX)
            else:
                raise

    return None


def extract_video_id(url):
    """
    从B站视频链接提取BV号或AV号
    支持格式:
    - https://www.bilibili.com/video/BV1xx411c7mD
    - https://www.bilibili.com/video/av170001
    - https://b23.tv/xxxxx (短链接)
    - BV1xx411c7mD (直接输入BV号)
    - av170001 (直接输入AV号)
    """
    url = url.strip()

    # 直接是BV号
    if re.match(r'^BV[a-zA-Z0-9]+$', url, re.IGNORECASE):
        return {"bvid": url}

    # 直接是AV号
    if re.match(r'^av\d+$', url, re.IGNORECASE):
        return {"aid": url[2:]}

    # 从URL提取BV号
    match = re.search(r'BV([a-zA-Z0-9]+)', url, re.IGNORECASE)
    if match:
        return {"bvid": "BV" + match.group(1)}

    # 从URL提取AV号
    match = re.search(r'av(\d+)', url, re.IGNORECASE)
    if match:
        return {"aid": match.group(1)}

    return None


def get_video_info(video_id, headers):
    """获取视频基本信息"""
    url = "https://api.bilibili.com/x/web-interface/view"

    response = _safe_request("GET", url, headers, video_id)
    if not response:
        return None

    data = response.json()
    if data.get("code") != 0:
        return None

    video_data = data["data"]
    return {
        "bvid": video_data.get("bvid", ""),
        "aid": video_data.get("aid", 0),
        "title": video_data.get("title", ""),
        "desc": video_data.get("desc", ""),
        "owner": video_data.get("owner", {}).get("name", ""),
        "owner_mid": video_data.get("owner", {}).get("mid", 0),
        "view": video_data.get("stat", {}).get("view", 0),
        "reply": video_data.get("stat", {}).get("reply", 0),
    }


def get_comments_page(oid, page, page_size, headers, sort=0):
    """
    获取一页评论
    oid: 视频aid
    page: 页码（从1开始）
    page_size: 每页数量
    sort: 排序方式 0=按时间 1=按点赞 2=按回复数
    """
    url = "https://api.bilibili.com/x/v2/reply"

    params = {
        "type": 1,  # 1表示视频
        "oid": oid,
        "pn": page,
        "ps": page_size,
        "sort": sort,
    }

    response = _safe_request("GET", url, headers, params)
    if not response:
        return None, 0

    data = response.json()
    if data.get("code") != 0:
        return None, 0

    replies = data.get("data", {}).get("replies", []) or []
    total = data.get("data", {}).get("page", {}).get("count", 0)

    return replies, total


def parse_comment(comment):
    """解析单条评论"""
    member = comment.get("member", {})
    content = comment.get("content", {})

    return {
        "评论ID": comment.get("rpid", 0),
        "用户名": member.get("uname", ""),
        "用户UID": member.get("mid", 0),
        "用户等级": member.get("level_info", {}).get("current_level", 0),
        "评论内容": content.get("message", ""),
        "发布时间": datetime.fromtimestamp(comment.get("ctime", 0)).strftime("%Y-%m-%d %H:%M:%S"),
        "点赞数": comment.get("like", 0),
        "回复数": comment.get("rcount", 0),
    }


def get_all_comments(aid, headers, max_comments=None, sort=0):
    """
    获取视频的所有评论（或指定数量）
    aid: 视频av号
    max_comments: 最大评论数，None表示全部
    sort: 排序方式
    """
    all_comments = []
    page = 1
    page_size = 20  # B站评论API每页最多20条

    # 先获取第一页，确定总数
    replies, total = get_comments_page(aid, page=1, page_size=page_size, headers=headers, sort=sort)
    if replies is None:
        return [], 0

    for reply in replies:
        all_comments.append(parse_comment(reply))
        if max_comments and len(all_comments) >= max_comments:
            break

    if max_comments and len(all_comments) >= max_comments:
        return all_comments[:max_comments], total

    # 计算需要获取的页数
    if max_comments:
        total_pages = math.ceil(min(max_comments, total) / page_size)
    else:
        total_pages = math.ceil(total / page_size)

    # 获取剩余页面
    for page in range(2, total_pages + 1):
        if max_comments and len(all_comments) >= max_comments:
            break

        _random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)

        replies, _ = get_comments_page(aid, page=page, page_size=page_size, headers=headers, sort=sort)
        if not replies:
            break

        for reply in replies:
            all_comments.append(parse_comment(reply))
            if max_comments and len(all_comments) >= max_comments:
                break

    if max_comments:
        return all_comments[:max_comments], total
    return all_comments, total


def sanitize_filename(name):
    """清理文件名，移除不合法字符"""
    return re.sub(r'[\\/:*?"<>|]', '_', name)[:50]


def scrape_video_comments(url_or_id, max_comments=None, sort=0):
    """
    爬取单个视频的评论
    url_or_id: 视频链接或BV/AV号
    max_comments: 最多爬取的评论数量，None表示全部
    sort: 排序方式 0=时间 1=点赞 2=回复
    返回: (成功/失败, 视频标题, 保存路径, 评论数量)
    """
    video_id = extract_video_id(url_or_id)
    if not video_id:
        print(f"  [错误] 无法从输入中提取视频ID: {url_or_id}")
        return False, None, None, 0

    headers = {
        "User-Agent": _get_random_ua(),
        "Referer": "https://www.bilibili.com/",
    }

    cookie = _optional_sessdata_cookie()
    if cookie:
        headers["Cookie"] = cookie

    # 获取视频信息
    video_info = get_video_info(video_id, headers)
    if not video_info:
        print(f"  [错误] 无法获取视频信息")
        return False, None, None, 0

    video_title = video_info["title"]
    bvid = video_info["bvid"]
    aid = video_info["aid"]

    print(f"  视频标题: {video_title[:40]}{'...' if len(video_title) > 40 else ''}")
    print(f"  UP主: {video_info['owner']} | 播放: {video_info['view']} | 评论: {video_info['reply']}")

    # 获取评论
    sort_names = {0: "时间", 1: "点赞", 2: "回复"}
    print(f"  正在获取评论（排序: {sort_names.get(sort, '时间')}）...")

    comments, total = get_all_comments(aid, headers, max_comments=max_comments, sort=sort)

    if not comments:
        print(f"  [警告] 未获取到评论")
        return False, video_title, None, 0

    print(f"  共获取 {len(comments)} 条评论（视频总评论数: {total}）")

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 生成文件名
    safe_title = sanitize_filename(video_title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_title}_{bvid}_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # 保存数据为CSV
    csv_headers = [
        "视频标题", "BV号", "AV号", "UP主", "UP主UID", "播放量", "评论总数",
        "视频简介", "视频链接", "爬取时间", "爬取评论数", "排序方式",
        "发布时间", "评论ID", "用户UID", "点赞数", "回复数",
        "用户等级", "用户名", "评论内容",
    ]

    crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sort_label = sort_names.get(sort, "时间")
    video_link = f"https://www.bilibili.com/video/{bvid}"

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        for c in comments:
            writer.writerow([
                video_title, bvid, f'="{aid}"', video_info["owner"],
                f'="{video_info["owner_mid"]}"', video_info["view"], total,
                video_info["desc"], video_link, crawl_time,
                len(comments), sort_label,
                c["发布时间"], f'="{c["评论ID"]}"', f'="{c["用户UID"]}"',
                c["点赞数"], c["回复数"], c["用户等级"], c["用户名"],
                c["评论内容"],
            ])

    return True, video_title, filepath, len(comments)


def main():
    global SESSDATA

    print("=" * 60)
    print("B站视频评论爬虫")
    print("=" * 60)

    # 获取SESSDATA
    print("\n【步骤1】请输入B站登录Cookie中的SESSDATA值")
    print("获取方法：浏览器登录B站 -> F12打开开发者工具 -> Application/应用程序")
    print("         -> Cookies -> bilibili.com -> 找到SESSDATA并复制值")
    print("(直接回车跳过，但部分视频评论可能无法获取)\n")

    try:
        sessdata_input = input("SESSDATA: ").strip()
        if sessdata_input:
            SESSDATA = sessdata_input
            print("✓ SESSDATA已设置\n")
        else:
            print("⚠ 未设置SESSDATA，将尝试无登录态爬取\n")
    except EOFError:
        pass

    # 获取排序方式
    print("-" * 60)
    print("\n【步骤2】选择评论排序方式")
    print("  0 - 按时间排序（默认）")
    print("  1 - 按点赞数排序")
    print("  2 - 按回复数排序")

    try:
        sort_input = input("\n排序方式 [0]: ").strip()
        sort = int(sort_input) if sort_input.isdigit() and int(sort_input) in [0, 1, 2] else 0
        sort_names = {0: "时间", 1: "点赞", 2: "回复"}
        print(f"✓ 已选择按{sort_names[sort]}排序\n")
    except (ValueError, EOFError):
        sort = 0

    print("-" * 60)
    print("\n【步骤3】请输入视频链接（支持多个，每行一个）")
    print("支持格式：")
    print("  - https://www.bilibili.com/video/BV1xx411c7mD")
    print("  - BV1xx411c7mD (直接输入BV号)")
    print("  - av170001 (直接输入AV号)")
    print("  - BV1xx411c7mD:100 (BV号:数量，只爬取前N条评论)")
    print("  - https://www.bilibili.com/video/BV1xx411c7mD:50 (链接:数量)")
    print("\n输入 'all' 或不加数量表示爬取全部评论")
    print("输入完成后，输入空行开始爬取\n")

    entries = []  # (url_or_id, max_comments)
    while True:
        try:
            line = input(f"[{len(entries)+1}] ").strip()
            if not line:
                if entries:
                    break
                else:
                    print("请至少输入一个视频链接")
                    continue

            # 解析是否带数量限制
            max_comments = None  # None表示全部
            if ":" in line:
                # 检查最后一个:后面是否是数字
                last_colon = line.rfind(":")
                after_colon = line[last_colon + 1:].strip()
                if after_colon.isdigit():
                    max_comments = int(after_colon)
                    line = line[:last_colon].strip()
                elif after_colon.lower() == "all":
                    max_comments = None
                    line = line[:last_colon].strip()

            entries.append((line, max_comments))
        except EOFError:
            break

    if not entries:
        print("未输入任何链接，退出")
        return

    print(f"\n{'=' * 60}")
    print(f"开始爬取 {len(entries)} 个视频的评论...")
    print(f"[防封禁模式] 请求间隔: {REQUEST_DELAY_MIN}-{REQUEST_DELAY_MAX}秒")
    print(f"{'=' * 60}\n")

    results = []
    for i, (url, max_comments) in enumerate(entries, 1):
        limit_str = f"前{max_comments}条" if max_comments else "全部"
        print(f"[{i}/{len(entries)}] 处理: {url} ({limit_str})")
        success, title, path, count = scrape_video_comments(url, max_comments=max_comments, sort=sort)

        if success:
            print(f"  ✓ 完成! {count} 条评论")
            print(f"    保存至: {path}\n")
            results.append((title, path, count, True))
        else:
            print(f"  ✗ 失败: 无法获取数据\n")
            results.append((title or url, None, 0, False))

        # 视频之间的间隔（除了最后一个）
        if i < len(entries):
            rest_time = random.uniform(VIDEO_DELAY_MIN, VIDEO_DELAY_MAX)
            print(f"  [防封禁] 等待 {rest_time:.1f} 秒后继续下一个视频...\n")
            time.sleep(rest_time)

    # 汇总报告
    print("\n" + "=" * 60)
    print("爬取完成！汇总报告：")
    print("=" * 60)

    success_count = sum(1 for r in results if r[3])
    print(f"\n成功: {success_count}/{len(results)}\n")

    print("保存路径：")
    for title, path, count, success in results:
        if success:
            display_title = title[:30] + "..." if len(title) > 30 else title
            print(f"  [{display_title}] {count}条评论 -> {path}")
        else:
            print(f"  [{title[:30] if title else 'Unknown'}] 失败")

    print(f"\n所有数据保存在: {os.path.abspath(OUTPUT_DIR)}/")


if __name__ == "__main__":
    main()
