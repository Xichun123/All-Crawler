"""
B站UP主视频数据爬虫
支持输入多个UP主主页链接，爬取所有视频的完整数据
每个UP主的数据单独保存为CSV文件
包含防封禁保护机制
"""

import requests
import csv
import os
import hashlib
import time
import re
import urllib.parse
import math
import random
from datetime import datetime


MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32,
    15, 50, 10, 31, 58, 3, 45, 35,
    27, 43, 5, 49, 33, 9, 42, 19,
    29, 28, 14, 39, 12, 38, 41, 13,
    37, 48, 7, 16, 24, 55, 40, 61,
    26, 17, 0, 1, 60, 51, 30, 4,
    22, 25, 54, 21, 56, 59, 6, 63,
    57, 62, 11, 36, 20, 34, 44, 52,
]

# 输出目录
OUTPUT_DIR = "bilibili_data"

# ============== 防封禁配置 ==============
# 请求间隔（秒）- 随机范围
REQUEST_DELAY_MIN = 0.5
REQUEST_DELAY_MAX = 1.5

# 分页请求间隔
PAGE_DELAY_MIN = 1.0
PAGE_DELAY_MAX = 2.0

# UP主之间的间隔
UP_DELAY_MIN = 3.0
UP_DELAY_MAX = 6.0

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


def _get_wbi_keys(headers):
    url = "https://api.bilibili.com/x/web-interface/nav"
    response = _safe_request("GET", url, headers)
    if not response:
        return None
    data = response.json()
    if data.get("code") != 0:
        return None
    wbi = data["data"]["wbi_img"]
    img_url = wbi.get("img_url", "")
    sub_url = wbi.get("sub_url", "")
    img_key = img_url.rsplit("/", 1)[-1].split(".", 1)[0]
    sub_key = sub_url.rsplit("/", 1)[-1].split(".", 1)[0]
    if not img_key or not sub_key:
        return None
    return img_key, sub_key


def _get_mixin_key(img_key, sub_key):
    raw = img_key + sub_key
    mixin = "".join(raw[i] for i in MIXIN_KEY_ENC_TAB)
    return mixin[:32]


def _sign_params(params, mixin_key):
    params = {k: str(v) for k, v in params.items()}
    params["wts"] = str(int(time.time()))
    for k in list(params.keys()):
        params[k] = re.sub(r"[!'()*]", "", params[k])
    query = urllib.parse.urlencode(sorted(params.items()))
    w_rid = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
    params["w_rid"] = w_rid
    return params


def extract_mid_from_url(url):
    """
    从B站用户主页链接提取UID
    支持格式:
    - https://space.bilibili.com/630399926
    - https://space.bilibili.com/630399926/video
    - space.bilibili.com/630399926
    - 630399926 (直接输入UID)
    """
    url = url.strip()

    # 直接是数字
    if url.isdigit():
        return url

    # 从URL提取
    match = re.search(r'space\.bilibili\.com/(\d+)', url)
    if match:
        return match.group(1)

    # 尝试匹配纯数字
    match = re.search(r'^(\d+)$', url)
    if match:
        return match.group(1)

    return None


def get_up_info(mid, headers, mixin_key):
    """获取UP主基本信息（昵称、简介等）"""
    # 使用 x/space/wbi/acc/info 接口，需要添加额外参数绕过风控
    url = "https://api.bilibili.com/x/space/wbi/acc/info"

    params = {
        "mid": mid,
        "platform": "web",
        "token": "",
        "web_location": "1550101",
    }
    params = _sign_params(params, mixin_key)

    response = _safe_request("GET", url, headers, params)

    # 如果主接口失败，尝试备用接口
    if not response:
        return _get_up_info_fallback(mid, headers)

    try:
        data = response.json()
    except Exception as e:
        return _get_up_info_fallback(mid, headers)

    if data.get("code") != 0:
        # 风控失败，使用备用方案
        return _get_up_info_fallback(mid, headers)

    user_data = data.get("data", {})
    return {
        "mid": mid,
        "name": user_data.get("name", ""),
        "sign": user_data.get("sign", ""),
        "level": user_data.get("level", 0),
        "official_title": user_data.get("official", {}).get("title", ""),
    }


def _get_up_info_fallback(mid, headers):
    """备用方案：从用户卡片接口获取UP主信息"""
    url = "https://api.bilibili.com/x/web-interface/card"
    params = {"mid": mid}

    response = _safe_request("GET", url, headers, params)
    if not response:
        return None

    try:
        data = response.json()
    except Exception:
        return None

    if data.get("code") != 0:
        return None

    card = data.get("data", {}).get("card", {})
    return {
        "mid": mid,
        "name": card.get("name", ""),
        "sign": card.get("sign", ""),
        "level": card.get("level_info", {}).get("current_level", 0),
        "official_title": card.get("official_verify", {}).get("desc", ""),
    }


def get_up_videos(mid, headers, mixin_key, page=1, page_size=50):
    """
    获取UP主的视频列表
    """
    url = "https://api.bilibili.com/x/space/wbi/arc/search"

    params = {
        "mid": mid,
        "ps": page_size,
        "pn": page,
        "order": "pubdate",
        "tid": 0,
    }

    params = _sign_params(params, mixin_key)

    response = _safe_request("GET", url, headers, params)
    if not response:
        return None, 0

    data = response.json()
    if data["code"] != 0:
        return None, 0

    total = data["data"]["page"]["count"]
    vlist = data["data"]["list"]["vlist"]
    return vlist, total


def get_all_videos(mid, headers, mixin_key):
    """获取UP主的所有视频"""
    all_videos = []
    page_size = 50

    videos, total = get_up_videos(mid, headers, mixin_key, page=1, page_size=page_size)
    if not videos:
        return [], 0

    all_videos.extend(videos)
    total_pages = math.ceil(total / page_size)

    for page in range(2, total_pages + 1):
        # 分页请求使用较长延迟
        _random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)
        videos, _ = get_up_videos(mid, headers, mixin_key, page=page, page_size=page_size)
        if videos:
            all_videos.extend(videos)
        else:
            break

    return all_videos, total


def get_limited_videos(mid, headers, mixin_key, max_count):
    """
    获取UP主的前N个视频（按发布时间排序，最新的在前）
    mid: UP主的用户ID
    max_count: 最多获取的视频数量
    返回: (视频列表, 总视频数)
    """
    all_videos = []
    page_size = min(50, max_count)  # 每页最多50，但如果只需要少量就用更小值
    page = 1

    while len(all_videos) < max_count:
        videos, total = get_up_videos(mid, headers, mixin_key, page=page, page_size=page_size)
        if not videos:
            break

        # 只取需要的数量
        remaining = max_count - len(all_videos)
        all_videos.extend(videos[:remaining])

        if len(videos) < page_size:
            # 没有更多视频了
            break

        page += 1
        if len(all_videos) < max_count:
            _random_delay(PAGE_DELAY_MIN, PAGE_DELAY_MAX)

    # 获取total（如果第一次请求成功的话）
    if all_videos:
        _, total = get_up_videos(mid, headers, mixin_key, page=1, page_size=1)
    else:
        total = 0

    return all_videos[:max_count], total


def get_video_stats(bvid, headers):
    """获取视频的详细统计数据"""
    url = "https://api.bilibili.com/x/web-interface/view"
    params = {"bvid": bvid}

    response = _safe_request("GET", url, headers, params)
    if not response:
        return None

    data = response.json()
    if data["code"] != 0:
        return None

    video_data = data["data"]
    stat = video_data["stat"]
    return {
        "desc": video_data.get("desc", ""),
        "view": stat["view"],
        "danmaku": stat["danmaku"],
        "reply": stat["reply"],
        "like": stat["like"],
        "coin": stat["coin"],
        "favorite": stat["favorite"],
        "share": stat["share"],
    }


def format_number(num):
    """格式化数字显示"""
    if num >= 10000:
        return f"{num/10000:.1f}万"
    return str(num)


def sanitize_filename(name):
    """清理文件名，移除不合法字符"""
    return re.sub(r'[\\/:*?"<>|]', '_', name)


def scrape_up(url_or_mid, max_videos=None):
    """
    爬取单个UP主的所有视频数据
    url_or_mid: UP主链接或UID
    max_videos: 最多爬取的视频数量，None表示全部
    返回: (成功/失败, UP主名称, 保存路径, 视频数量)
    """
    mid = extract_mid_from_url(url_or_mid)
    if not mid:
        print(f"  [错误] 无法从输入中提取UID: {url_or_mid}")
        return False, None, None, 0

    headers = {
        "User-Agent": _get_random_ua(),
        "Referer": f"https://space.bilibili.com/{mid}/video",
    }

    cookie = _optional_sessdata_cookie()
    if cookie:
        headers["Cookie"] = cookie
    else:
        print("  [提示] 未设置BILIBILI_SESSDATA，部分UP主可能无法获取")

    # 获取WBI keys
    wbi_keys = _get_wbi_keys(headers)
    if not wbi_keys:
        print("  [错误] 无法获取WBI keys，请检查网络或设置BILIBILI_SESSDATA")
        return False, None, None, 0
    mixin_key = _get_mixin_key(wbi_keys[0], wbi_keys[1])

    # 获取UP主信息
    up_info = get_up_info(mid, headers, mixin_key)
    if not up_info:
        print(f"  [警告] 无法获取UP主信息，使用UID作为名称")
    up_name = up_info["name"] if up_info else f"UID_{mid}"

    print(f"  正在获取 [{up_name}] (UID: {mid}) 的视频列表...")

    # 获取视频（支持限制数量）
    if max_videos:
        videos, total = get_limited_videos(mid, headers, mixin_key, max_videos)
        print(f"  UP主共有 {total} 个视频，本次爬取最新 {len(videos)} 个")
    else:
        videos, total = get_all_videos(mid, headers, mixin_key)
        print(f"  共 {total} 个视频，正在获取详细数据...")

    if not videos:
        print(f"  [错误] 获取视频列表失败，该UP主可能没有视频或需要登录态")
        return False, up_name, None, 0

    print(f"  正在获取 {len(videos)} 个视频的详细数据...")

    # 获取每个视频的详细数据
    results = []
    for i, video in enumerate(videos, 1):
        title = video["title"]
        bvid = video["bvid"]

        stats = get_video_stats(bvid, headers)

        if stats:
            results.append({
                "序号": i,
                "标题": title,
                "BV号": bvid,
                "简介": stats["desc"],
                "播放量": stats["view"],
                "弹幕数": stats["danmaku"],
                "评论数": stats["reply"],
                "点赞": stats["like"],
                "投币": stats["coin"],
                "收藏": stats["favorite"],
                "转发": stats["share"],
                "链接": f"https://www.bilibili.com/video/{bvid}"
            })

        # 进度提示（每50个）
        if i % 50 == 0:
            print(f"    已处理 {i}/{len(videos)} 个视频...")

        # 请求间隔，使用随机延迟防封禁
        _random_delay(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX)

    if not results:
        return False, up_name, None, 0

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 生成文件名
    safe_name = sanitize_filename(up_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_name}_UID{mid}_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # 计算汇总数据
    summary = {
        "总播放量": sum(r["播放量"] for r in results),
        "总弹幕数": sum(r["弹幕数"] for r in results),
        "总评论数": sum(r["评论数"] for r in results),
        "总点赞": sum(r["点赞"] for r in results),
        "总投币": sum(r["投币"] for r in results),
        "总收藏": sum(r["收藏"] for r in results),
        "总转发": sum(r["转发"] for r in results),
    }

    # 保存数据为CSV
    csv_headers = [
        "UP主昵称", "UID", "个人简介", "等级", "认证信息", "主页",
        "爬取时间", "视频总数",
        "总播放量", "总弹幕数", "总评论数", "总点赞", "总投币", "总收藏", "总转发",
        "序号", "标题", "BV号", "简介", "播放量", "弹幕数", "评论数",
        "点赞", "投币", "收藏", "转发", "链接",
    ]

    crawl_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    up_sign = up_info["sign"] if up_info else ""
    up_level = up_info["level"] if up_info else 0
    up_official = up_info["official_title"] if up_info else ""
    up_home = f"https://space.bilibili.com/{mid}"

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        for r in results:
            writer.writerow([
                up_name, f'="{mid}"', up_sign, up_level, up_official, up_home,
                crawl_time, len(results),
                summary["总播放量"], summary["总弹幕数"], summary["总评论数"],
                summary["总点赞"], summary["总投币"], summary["总收藏"],
                summary["总转发"],
                r["序号"], r["标题"], r["BV号"], r["简介"], r["播放量"],
                r["弹幕数"], r["评论数"], r["点赞"], r["投币"], r["收藏"],
                r["转发"], r["链接"],
            ])

    return True, up_name, filepath, len(results)


def main():
    global SESSDATA

    print("=" * 60)
    print("B站UP主视频数据爬虫")
    print("=" * 60)

    # 获取SESSDATA
    print("\n【步骤1】请输入B站登录Cookie中的SESSDATA值")
    print("获取方法：浏览器登录B站 -> F12打开开发者工具 -> Application/应用程序")
    print("         -> Cookies -> bilibili.com -> 找到SESSDATA并复制值")
    print("(直接回车跳过，但部分UP主可能无法爬取)\n")

    try:
        sessdata_input = input("SESSDATA: ").strip()
        if sessdata_input:
            SESSDATA = sessdata_input
            print("✓ SESSDATA已设置\n")
        else:
            print("⚠ 未设置SESSDATA，将尝试无登录态爬取\n")
    except EOFError:
        pass

    print("-" * 60)
    print("\n【步骤2】请输入UP主主页链接（支持多个，每行一个）")
    print("支持格式：")
    print("  - https://space.bilibili.com/630399926")
    print("  - space.bilibili.com/630399926")
    print("  - 630399926 (直接输入UID)")
    print("  - 630399926:50 (UID:数量，只爬取最新N个视频)")
    print("  - https://space.bilibili.com/630399926:100 (链接:数量)")
    print("\n输入 'all' 或不加数量表示爬取全部视频")
    print("输入完成后，输入空行开始爬取\n")

    entries = []  # (url_or_mid, max_videos)
    while True:
        try:
            line = input(f"[{len(entries)+1}] ").strip()
            if not line:
                if entries:
                    break
                else:
                    print("请至少输入一个UP主链接")
                    continue

            # 解析是否带数量限制
            max_videos = None  # None表示全部
            if ":" in line:
                # 检查最后一个:后面是否是数字
                last_colon = line.rfind(":")
                after_colon = line[last_colon + 1:].strip()
                if after_colon.isdigit():
                    max_videos = int(after_colon)
                    line = line[:last_colon].strip()
                elif after_colon.lower() == "all":
                    max_videos = None
                    line = line[:last_colon].strip()

            entries.append((line, max_videos))
        except EOFError:
            break

    if not entries:
        print("未输入任何链接，退出")
        return

    print(f"\n{'=' * 60}")
    print(f"开始爬取 {len(entries)} 个UP主的数据...")
    print(f"[防封禁模式] 请求间隔: {REQUEST_DELAY_MIN}-{REQUEST_DELAY_MAX}秒")
    print(f"{'=' * 60}\n")

    results = []
    for i, (url, max_videos) in enumerate(entries, 1):
        limit_str = f"最新{max_videos}个" if max_videos else "全部"
        print(f"[{i}/{len(entries)}] 处理: {url} ({limit_str})")
        success, name, path, count = scrape_up(url, max_videos=max_videos)

        if success:
            print(f"  ✓ 完成! {count} 个视频")
            print(f"    保存至: {path}\n")
            results.append((name, path, count, True))
        else:
            print(f"  ✗ 失败: 无法获取数据\n")
            results.append((name or url, None, 0, False))

        # UP主之间的间隔（除了最后一个）
        if i < len(entries):
            rest_time = random.uniform(UP_DELAY_MIN, UP_DELAY_MAX)
            print(f"  [防封禁] 等待 {rest_time:.1f} 秒后继续下一个UP主...\n")
            time.sleep(rest_time)

    # 汇总报告
    print("\n" + "=" * 60)
    print("爬取完成！汇总报告：")
    print("=" * 60)

    success_count = sum(1 for r in results if r[3])
    print(f"\n成功: {success_count}/{len(results)}\n")

    print("保存路径：")
    for name, path, count, success in results:
        if success:
            print(f"  [{name}] {count}个视频 -> {path}")
        else:
            print(f"  [{name}] 失败")

    print(f"\n所有数据保存在: {os.path.abspath(OUTPUT_DIR)}/")


if __name__ == "__main__":
    main()
