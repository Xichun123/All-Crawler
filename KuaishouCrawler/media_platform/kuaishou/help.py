# -*- coding: utf-8 -*-
# 快手爬虫 - URL解析工具 (从 MediaCrawler 移植)
# 仅供学习和研究使用，请遵守平台使用条款

import re
from model.m_kuaishou import VideoUrlInfo, CreatorUrlInfo


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    """
    Parse video ID from Kuaishou video URL
    Supports the following formats:
    1. Full video URL: "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs&streamSource=search"
    2. Pure video ID: "3x3zxz4mjrsc8ke"

    Args:
        url: Kuaishou video link or video ID
    Returns:
        VideoUrlInfo: Object containing video ID
    """
    # If it doesn't contain http and doesn't contain kuaishou.com, consider it as pure ID
    if not url.startswith("http") and "kuaishou.com" not in url:
        return VideoUrlInfo(video_id=url, url_type="normal")

    # Extract ID from standard video URL: /short-video/video_ID
    video_pattern = r'/short-video/([a-zA-Z0-9_-]+)'
    match = re.search(video_pattern, url)
    if match:
        video_id = match.group(1)
        return VideoUrlInfo(video_id=video_id, url_type="normal")

    raise ValueError(f"Unable to parse video ID from URL: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    """
    Parse creator ID from Kuaishou creator homepage URL
    Supports the following formats:
    1. Creator homepage: "https://www.kuaishou.com/profile/3x84qugg4ch9zhs"
    2. Pure ID: "3x4sm73aye7jq7i"

    Args:
        url: Kuaishou creator homepage link or user_id
    Returns:
        CreatorUrlInfo: Object containing creator ID
    """
    # If it doesn't contain http and doesn't contain kuaishou.com, consider it as pure ID
    if not url.startswith("http") and "kuaishou.com" not in url:
        return CreatorUrlInfo(user_id=url)

    # Extract user_id from creator homepage URL: /profile/xxx
    user_pattern = r'/profile/([a-zA-Z0-9_-]+)'
    match = re.search(user_pattern, url)
    if match:
        user_id = match.group(1)
        return CreatorUrlInfo(user_id=user_id)

    raise ValueError(f"Unable to parse creator ID from URL: {url}")


if __name__ == '__main__':
    # Test video URL parsing
    print("=== Video URL Parsing Test ===")
    test_video_urls = [
        "https://www.kuaishou.com/short-video/3x3zxz4mjrsc8ke?authorId=3x84qugg4ch9zhs&streamSource=search&area=searchxxnull&searchKey=python",
        "3xf8enb8dbj6uig",
    ]
    for url in test_video_urls:
        try:
            result = parse_video_info_from_url(url)
            print(f"URL: {url[:80]}...")
            print(f"  Result: {result}\n")
        except Exception as e:
            print(f"URL: {url}")
            print(f"  Error: {e}\n")

    # Test creator URL parsing
    print("=== Creator URL Parsing Test ===")
    test_creator_urls = [
        "https://www.kuaishou.com/profile/3x84qugg4ch9zhs",
        "3x4sm73aye7jq7i",
    ]
    for url in test_creator_urls:
        try:
            result = parse_creator_info_from_url(url)
            print(f"URL: {url[:80]}...")
            print(f"  Result: {result}\n")
        except Exception as e:
            print(f"URL: {url}")
            print(f"  Error: {e}\n")
