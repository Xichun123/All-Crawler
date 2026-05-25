# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/douyin/core.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

import asyncio
import os
import random
import urllib.parse
from asyncio import Task
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import (
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
    async_playwright,
)

import config
from base.base_crawler import AbstractCrawler
from proxy.proxy_ip_pool import IpInfoModel, create_ip_pool
from store import douyin as douyin_store
from tools import utils
from tools.cdp_browser import CDPBrowserManager
from tools.clean_writer import (
    write_creator_result,
    write_creator_search_result,
    write_detail_result,
    write_search_result,
)
from var import crawler_type_var, source_keyword_var

from .client import DouYinClient
from .exception import DataFetchError
from .field import PublishTimeType
from .help import parse_video_info_from_url, parse_creator_info_from_url
from .login import DouYinLogin


class DouYinCrawler(AbstractCrawler):
    context_page: Page
    dy_client: DouYinClient
    browser_context: BrowserContext
    cdp_manager: Optional[CDPBrowserManager]

    def __init__(self) -> None:
        self.index_url = "https://www.douyin.com"
        self.cdp_manager = None
        self.ip_proxy_pool = None  # 代理IP池，用于代理自动刷新

    async def start(self) -> None:
        playwright_proxy_format, httpx_proxy_format = None, None
        if config.ENABLE_IP_PROXY:
            self.ip_proxy_pool = await create_ip_pool(config.IP_PROXY_POOL_COUNT, enable_validate_ip=True)
            ip_proxy_info: IpInfoModel = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = utils.format_proxy_info(ip_proxy_info)

        async with async_playwright() as playwright:
            # 根据配置选择启动模式
            if config.ENABLE_CDP_MODE:
                utils.logger.info("[DouYinCrawler] 使用CDP模式启动浏览器")
                self.browser_context = await self.launch_browser_with_cdp(
                    playwright,
                    playwright_proxy_format,
                    None,
                    headless=config.CDP_HEADLESS,
                )
            else:
                utils.logger.info("[DouYinCrawler] 使用标准模式启动浏览器")
                # Launch a browser context.
                chromium = playwright.chromium
                self.browser_context = await self.launch_browser(
                    chromium,
                    playwright_proxy_format,
                    user_agent=None,
                    headless=config.HEADLESS,
                )
                # stealth.min.js is a js script to prevent the website from detecting the crawler.
                await self.browser_context.add_init_script(path="libs/stealth.min.js")

            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.dy_client = await self.create_douyin_client(httpx_proxy_format)
            if not await self.dy_client.pong(browser_context=self.browser_context):
                login_obj = DouYinLogin(
                    login_type=config.LOGIN_TYPE,
                    login_phone="",  # you phone number
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(browser_context=self.browser_context)
            crawler_type_var.set(config.CRAWLER_TYPE)
            if config.CRAWLER_TYPE == "search":
                # Search for notes and retrieve their comment information.
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                # Get the information and comments of the specified post
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                # Get the information and comments of the specified creator
                await self.get_creators_and_videos()
            elif config.CRAWLER_TYPE in {"creator-search", "creator_search"}:
                await self.search_creator_videos()
            else:
                raise ValueError(f"Unsupported crawler type: {config.CRAWLER_TYPE}")

            utils.logger.info("[DouYinCrawler.start] Douyin Crawler finished ...")

    async def search(self) -> None:
        utils.logger.info("[DouYinCrawler.search] Begin search douyin keywords")
        dy_limit_count = 10  # douyin limit page fixed value
        if config.CRAWLER_MAX_NOTES_COUNT < dy_limit_count:
            config.CRAWLER_MAX_NOTES_COUNT = dy_limit_count
        start_page = config.START_PAGE  # start page number
        for keyword in config.KEYWORDS.split(","):
            source_keyword_var.set(keyword)
            utils.logger.info(f"[DouYinCrawler.search] Current keyword: {keyword}")
            aweme_list: List[str] = []
            keyword_videos: List[Dict] = []  # 收集该关键词下所有视频原始数据
            self._collected_comments: Dict[str, List[Dict]] = {}
            page = 0
            dy_search_id = ""
            while (page - start_page + 1) * dy_limit_count <= config.CRAWLER_MAX_NOTES_COUNT:
                if page < start_page:
                    utils.logger.info(f"[DouYinCrawler.search] Skip {page}")
                    page += 1
                    continue
                try:
                    utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page}")
                    posts_res = await self.dy_client.search_info_by_keyword(
                        keyword=keyword,
                        offset=page * dy_limit_count - dy_limit_count,
                        publish_time=PublishTimeType(config.PUBLISH_TIME_TYPE),
                        search_id=dy_search_id,
                    )
                    if posts_res.get("data") is None or posts_res.get("data") == []:
                        utils.logger.info(f"[DouYinCrawler.search] search douyin keyword: {keyword}, page: {page} is empty,{posts_res.get('data')}`")
                        break
                except DataFetchError:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed")
                    break

                page += 1
                if "data" not in posts_res:
                    utils.logger.error(f"[DouYinCrawler.search] search douyin keyword: {keyword} failed，账号也许被风控了。")
                    break
                dy_search_id = posts_res.get("extra", {}).get("logid", "")
                page_aweme_list = []
                for post_item in posts_res.get("data"):
                    try:
                        aweme_info: Dict = (post_item.get("aweme_info") or post_item.get("aweme_mix_info", {}).get("mix_items")[0])
                    except TypeError:
                        continue
                    aweme_list.append(aweme_info.get("aweme_id", ""))
                    page_aweme_list.append(aweme_info.get("aweme_id", ""))
                    keyword_videos.append(aweme_info)
                    await self.get_aweme_media(aweme_item=aweme_info)

                # Batch get note comments for the current page
                await self.batch_get_note_comments(page_aweme_list)

                # Sleep after each page navigation
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[DouYinCrawler.search] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after page {page-1}")
            utils.logger.info(f"[DouYinCrawler.search] keyword:{keyword}, aweme_list:{aweme_list}")
            # 写入整洁 JSON
            if keyword_videos:
                write_search_result(keyword, keyword_videos, self._collected_comments)

    async def get_specified_awemes(self):
        """Get the information and comments of the specified post from URLs or IDs"""
        utils.logger.info("[DouYinCrawler.get_specified_awemes] Parsing video URLs...")
        aweme_id_list = []
        for video_url in config.DY_SPECIFIED_ID_LIST:
            try:
                video_info = parse_video_info_from_url(video_url)

                # 处理短链接
                if video_info.url_type == "short":
                    utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Resolving short link: {video_url}")
                    resolved_url = await self.dy_client.resolve_short_url(video_url)
                    if resolved_url:
                        # 从解析后的URL中提取视频ID
                        video_info = parse_video_info_from_url(resolved_url)
                        utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Short link resolved to aweme ID: {video_info.aweme_id}")
                    else:
                        utils.logger.error(f"[DouYinCrawler.get_specified_awemes] Failed to resolve short link: {video_url}")
                        continue

                aweme_id_list.append(video_info.aweme_id)
                utils.logger.info(f"[DouYinCrawler.get_specified_awemes] Parsed aweme ID: {video_info.aweme_id} from {video_url}")
            except ValueError as e:
                utils.logger.error(f"[DouYinCrawler.get_specified_awemes] Failed to parse video URL: {e}")
                continue

        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(aweme_id=aweme_id, semaphore=semaphore) for aweme_id in aweme_id_list]
        aweme_details = await asyncio.gather(*task_list)
        collected: List[Dict] = []
        for aweme_detail in aweme_details:
            if aweme_detail is not None:
                collected.append(aweme_detail)
                await self.get_aweme_media(aweme_item=aweme_detail)
        self._collected_comments: Dict[str, List[Dict]] = {}
        await self.batch_get_note_comments(aweme_id_list)
        # 写入整洁 JSON
        if collected:
            write_detail_result(collected, self._collected_comments)

    async def get_aweme_detail(self, aweme_id: str, semaphore: asyncio.Semaphore) -> Any:
        """Get note detail"""
        async with semaphore:
            try:
                result = await self.dy_client.get_video_by_id(aweme_id)
                # Sleep after fetching aweme detail
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
                utils.logger.info(f"[DouYinCrawler.get_aweme_detail] Sleeping for {config.CRAWLER_MAX_SLEEP_SEC} seconds after fetching aweme {aweme_id}")
                return result
            except DataFetchError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] Get aweme detail error: {ex}")
                return None
            except KeyError as ex:
                utils.logger.error(f"[DouYinCrawler.get_aweme_detail] have not fund note detail aweme_id:{aweme_id}, err: {ex}")
                return None

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        """
        Batch get note comments
        """
        if not config.ENABLE_GET_COMMENTS:
            utils.logger.info(f"[DouYinCrawler.batch_get_note_comments] Crawling comment mode is not enabled")
            return

        task_list: List[Task] = []
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        for aweme_id in aweme_list:
            task = asyncio.create_task(self.get_comments(aweme_id, semaphore), name=aweme_id)
            task_list.append(task)
        if len(task_list) > 0:
            await asyncio.wait(task_list)

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            try:
                # 将关键词列表传递给 get_aweme_all_comments 方法
                # Use fixed crawling interval
                crawl_interval = config.CRAWLER_MAX_SLEEP_SEC
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=crawl_interval,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=self._collect_comment,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
                # Sleep after fetching comments
                await asyncio.sleep(crawl_interval)
                utils.logger.info(f"[DouYinCrawler.get_comments] Sleeping for {crawl_interval} seconds after fetching comments for aweme {aweme_id}")
                utils.logger.info(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} comments have all been obtained and filtered ...")
            except DataFetchError as e:
                utils.logger.error(f"[DouYinCrawler.get_comments] aweme_id: {aweme_id} get comments failed, error: {e}")

    async def _collect_comment(self, aweme_id: str, comments: List[Dict]) -> None:
        """收集评论到内存 dict，按 aweme_id 分组"""
        if aweme_id not in self._collected_comments:
            self._collected_comments[aweme_id] = []
        self._collected_comments[aweme_id].extend(comments)

    async def get_creators_and_videos(self) -> None:
        """
        Get the information and videos of the specified creator from URLs or IDs
        """
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Begin get douyin creators")
        utils.logger.info("[DouYinCrawler.get_creators_and_videos] Parsing creator URLs...")

        for creator_url in config.DY_CREATOR_ID_LIST:
            try:
                creator_info_parsed = parse_creator_info_from_url(creator_url)
                user_id = creator_info_parsed.sec_user_id
                utils.logger.info(f"[DouYinCrawler.get_creators_and_videos] Parsed sec_user_id: {user_id} from {creator_url}")
            except ValueError as e:
                utils.logger.error(f"[DouYinCrawler.get_creators_and_videos] Failed to parse creator URL: {e}")
                continue

            creator_info: Dict = await self.dy_client.get_user_info(user_id)

            # 收集该作者的所有视频
            self._collected_videos: List[Dict] = []
            self._collected_comments: Dict[str, List[Dict]] = {}

            # Get all video information of the creator
            all_video_list = await self.dy_client.get_all_user_aweme_posts(
                sec_user_id=user_id,
                callback=self.fetch_creator_video_detail,
                max_count=config.CRAWLER_MAX_NOTES_COUNT,
            )

            video_ids = [video_item.get("aweme_id") for video_item in all_video_list]
            await self.batch_get_note_comments(video_ids)

            # 写入整洁 JSON
            if creator_info:
                write_creator_result(creator_info, self._collected_videos, self._collected_comments)

    async def fetch_creator_video_detail(self, video_list: List[Dict]):
        """
        Concurrently obtain the specified post list and save the data
        """
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        task_list = [self.get_aweme_detail(post_item.get("aweme_id"), semaphore) for post_item in video_list]

        note_details = await asyncio.gather(*task_list)
        for aweme_item in note_details:
            if aweme_item is not None:
                self._collected_videos.append(aweme_item)
                await self.get_aweme_media(aweme_item=aweme_item)

    async def search_creator_videos(self) -> None:
        """
        Search videos inside creator homepages through the visible page UI.
        This flow depends on Douyin's creator-page toolbar and reuses the
        configured browser/login context instead of launching a second browser.
        """
        keyword = config.CREATOR_SEARCH_KEYWORD.strip()
        if not keyword:
            raise ValueError("creator-search mode requires creator_search_keyword or CLI keyword")

        for creator_url in config.DY_CREATOR_ID_LIST:
            source_url = self._creator_home_url(creator_url)
            utils.logger.info(
                f"[DouYinCrawler.search_creator_videos] Search creator page: {source_url}, keyword: {keyword}"
            )
            await self.context_page.goto(source_url, wait_until="domcontentloaded", timeout=60000)
            await self.context_page.wait_for_timeout(5000)

            creator = await self._extract_visible_creator_info(creator_url)
            await self._open_creator_search(keyword)
            videos = await self._collect_creator_search_videos(config.CRAWLER_MAX_NOTES_COUNT)
            final_url = self.context_page.url
            write_creator_search_result(
                creator=creator,
                keyword=keyword,
                source_url=source_url,
                final_url=final_url,
                target_count=config.CRAWLER_MAX_NOTES_COUNT,
                videos_raw=videos,
            )

    def _creator_home_url(self, creator_url: str) -> str:
        if creator_url.startswith("http"):
            return creator_url
        creator_info = parse_creator_info_from_url(creator_url)
        return f"https://www.douyin.com/user/{urllib.parse.quote(creator_info.sec_user_id, safe='')}"

    async def _extract_visible_creator_info(self, creator_url: str) -> Dict:
        try:
            nickname = (await self.context_page.locator("h1").first.inner_text(timeout=2000)).strip()
        except Exception:
            nickname = ""

        sec_uid = ""
        try:
            sec_uid = parse_creator_info_from_url(creator_url).sec_user_id
        except ValueError:
            pass

        return {
            "昵称": nickname,
            "sec_uid": sec_uid,
            "主页链接": self._creator_home_url(creator_url),
        }

    async def _open_creator_search(self, keyword: str) -> None:
        search_input = self.context_page.locator('input[placeholder*="搜索 Ta 的作品"], input[placeholder*="搜索Ta的作品"]').last
        try:
            await search_input.click(timeout=3000)
        except Exception:
            try:
                await self.context_page.get_by_text("搜索 Ta 的作品", exact=False).last.click(timeout=3000)
            except Exception:
                try:
                    await self.context_page.get_by_text("搜索Ta的视频", exact=False).last.click(timeout=3000)
                except Exception:
                    await self._click_creator_toolbar_search()

        await self.context_page.wait_for_timeout(800)
        search_box = self.context_page.locator(
            'input[placeholder*="搜索"], textarea[placeholder*="搜索"], [contenteditable="true"]'
        ).last
        await search_box.click(timeout=5000)
        await self.context_page.keyboard.press("Control+A")
        await self.context_page.keyboard.type(keyword, delay=60)
        await self.context_page.keyboard.press("Enter")
        await self.context_page.wait_for_timeout(5000)

    async def _click_creator_toolbar_search(self) -> None:
        box = await self.context_page.evaluate(
            """() => {
                const candidates = [...document.querySelectorAll('button, div, span, a')]
                    .map((el) => {
                        const rect = el.getBoundingClientRect();
                        const text = (el.innerText || el.getAttribute('aria-label') || '').trim();
                        return { rect, text };
                    })
                    .filter((x) => x.rect.width > 0 && x.rect.height > 0)
                    .filter((x) => x.rect.y > 200)
                    .filter((x) => /搜索\\s*(TA|Ta|ta)?\\s*的(视频|作品)|搜索.*(视频|作品)/.test(x.text))
                    .sort((a, b) => (b.rect.width * b.rect.height) - (a.rect.width * a.rect.height));
                const target = candidates[0];
                if (!target) return null;
                return {
                    x: target.rect.left + target.rect.width / 2,
                    y: target.rect.top + target.rect.height / 2
                };
            }"""
        )
        if not box:
            raise RuntimeError("Unable to find creator-page internal search entry")
        await self.context_page.mouse.click(box["x"], box["y"])

    async def _collect_creator_search_videos(self, count: int) -> List[Dict]:
        page_total = await self._get_search_result_count()
        if page_total is not None and page_total > 0:
            count = min(count, page_total)
            utils.logger.info(
                f"[DouYinCrawler.search_creator_videos] page reports {page_total} results, capping at {count}"
            )

        all_items: List[Dict] = []
        stable_rounds = 0
        last_count = 0
        max_scrolls = max(1, config.CREATOR_SEARCH_MAX_SCROLLS)
        stable_limit = max(1, config.CREATOR_SEARCH_STABLE_ROUNDS)

        for _ in range(max_scrolls):
            all_items = self._dedupe_visible_videos(
                all_items + await self._collect_search_result_videos()
            )
            utils.logger.info(
                f"[DouYinCrawler.search_creator_videos] collected={len(all_items)} url={self.context_page.url}"
            )
            if len(all_items) >= count:
                break

            if len(all_items) == last_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                last_count = len(all_items)
            if stable_rounds >= stable_limit:
                break

            await self.context_page.mouse.wheel(0, 1800)
            await self.context_page.wait_for_timeout(1200)

        return all_items[:count]

    async def _get_search_result_count(self) -> Optional[int]:
        """从页面"找到该用户的X个相关视频"提取搜索结果总数"""
        import re
        try:
            text = await self.context_page.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('*')].find(
                        e => /找到该用户的\\d+个相关视频/.test(e.innerText) && e.children.length === 0
                    );
                    return el ? el.innerText : '';
                }"""
            )
            m = re.search(r"找到该用户的(\d+)个相关视频", text)
            return int(m.group(1)) if m else None
        except Exception:
            return None

    async def _collect_search_result_videos(self) -> List[Dict]:
        """只收集搜索结果区域内的视频，排除推荐区域"""
        return await self.context_page.evaluate(
            """() => {
                // 找到"找到该用户的X个相关视频"所在的容器
                const hint = [...document.querySelectorAll('*')].find(
                    e => /找到该用户的\\d+个相关视频/.test(e.innerText) && e.children.length === 0
                );
                // 搜索结果容器：hint 的父级中包含视频链接的最近祖先
                let container = hint;
                if (container) {
                    while (container && container !== document.body) {
                        container = container.parentElement;
                        if (container && container.querySelectorAll('a[href*="/video/"]').length > 0) break;
                    }
                }
                if (!container || container === document.body) container = null;

                const scope = container || document;
                return Array.from(scope.querySelectorAll('a[href*="/video/"]')).map((a) => {
                    const href = new URL(a.getAttribute('href'), location.href).href.split('?')[0];
                    const match = href.match(/\\/video\\/(\\d+)/);
                    const img = a.querySelector('img');
                    const textParts = [
                        a.innerText,
                        a.getAttribute('aria-label'),
                        a.getAttribute('title'),
                        img && img.getAttribute('alt')
                    ].filter(Boolean).map((v) => String(v).trim()).filter(Boolean);
                    return {
                        video_id: match ? match[1] : "",
                        aweme_id: match ? match[1] : "",
                        video_url: href,
                        title: textParts[0] || ""
                    };
                });
            }"""
        )

    async def _collect_visible_videos(self) -> List[Dict]:
        return await self.context_page.evaluate(
            """() => Array.from(document.querySelectorAll('a[href*="/video/"]')).map((a) => {
                const href = new URL(a.getAttribute('href'), location.href).href.split('?')[0];
                const match = href.match(/\\/video\\/(\\d+)/);
                const img = a.querySelector('img');
                const textParts = [
                    a.innerText,
                    a.getAttribute('aria-label'),
                    a.getAttribute('title'),
                    img && img.getAttribute('alt')
                ].filter(Boolean).map((v) => String(v).trim()).filter(Boolean);
                return {
                    video_id: match ? match[1] : "",
                    aweme_id: match ? match[1] : "",
                    video_url: href,
                    title: textParts[0] || ""
                };
            })"""
        )

    def _dedupe_visible_videos(self, items: List[Dict]) -> List[Dict]:
        seen = set()
        result = []
        for item in items:
            video_id = item.get("video_id") or item.get("aweme_id")
            if not video_id or video_id in seen:
                continue
            seen.add(video_id)
            result.append(item)
        return result

    async def create_douyin_client(self, httpx_proxy: Optional[str]) -> DouYinClient:
        """Create douyin client"""
        cookie_str, cookie_dict = utils.convert_cookies(await self.browser_context.cookies())  # type: ignore
        douyin_client = DouYinClient(
            proxy=httpx_proxy,
            headers={
                "User-Agent": await self.context_page.evaluate("() => navigator.userAgent"),
                "Cookie": cookie_str,
                "Host": "www.douyin.com",
                "Origin": "https://www.douyin.com/",
                "Referer": "https://www.douyin.com/",
                "Content-Type": "application/json;charset=UTF-8",
            },
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,  # 传递代理池用于自动刷新
        )
        return douyin_client

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """Launch browser and create browser context"""
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(os.getcwd(), "browser_data", config.USER_DATA_DIR % config.PLATFORM)  # type: ignore
            browser_context = await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,  # type: ignore
                viewport={
                    "width": 1920,
                    "height": 1080
                },
                user_agent=user_agent,
            )  # type: ignore
            return browser_context
        else:
            browser = await chromium.launch(headless=headless, proxy=playwright_proxy)  # type: ignore
            browser_context = await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)
            return browser_context

    async def launch_browser_with_cdp(
        self,
        playwright: Playwright,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        """
        使用CDP模式启动浏览器
        """
        try:
            self.cdp_manager = CDPBrowserManager()
            browser_context = await self.cdp_manager.launch_and_connect(
                playwright=playwright,
                playwright_proxy=playwright_proxy,
                user_agent=user_agent,
                headless=headless,
            )

            # 添加反检测脚本
            await self.cdp_manager.add_stealth_script()

            # 显示浏览器信息
            browser_info = await self.cdp_manager.get_browser_info()
            utils.logger.info(f"[DouYinCrawler] CDP浏览器信息: {browser_info}")

            return browser_context

        except Exception as e:
            utils.logger.error(f"[DouYinCrawler] CDP模式启动失败，回退到标准模式: {e}")
            # 回退到标准模式
            chromium = playwright.chromium
            return await self.launch_browser(chromium, playwright_proxy, user_agent, headless)

    async def close(self) -> None:
        """Close browser context"""
        # 如果使用CDP模式，需要特殊处理
        if self.cdp_manager:
            await self.cdp_manager.cleanup()
            self.cdp_manager = None
        else:
            await self.browser_context.close()
        utils.logger.info("[DouYinCrawler.close] Browser context closed ...")

    async def get_aweme_media(self, aweme_item: Dict):
        """
        获取抖音媒体，自动判断媒体类型是短视频还是帖子图片并下载

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            utils.logger.info(f"[DouYinCrawler.get_aweme_media] Crawling image mode is not enabled")
            return
        # 笔记 urls 列表，若为短视频类型则返回为空列表
        note_download_url: List[str] = douyin_store._extract_note_image_list(aweme_item)
        # 视频 url，永远存在，但为短视频类型时的文件其实是音频文件
        video_download_url: str = douyin_store._extract_video_download_url(aweme_item)
        # TODO: 抖音并没采用音视频分离的策略，故音频可从原视频中分离，暂不提取
        if note_download_url:
            await self.get_aweme_images(aweme_item)
        else:
            await self.get_aweme_video(aweme_item)

    async def get_aweme_images(self, aweme_item: Dict):
        """
        get aweme images. please use get_aweme_media

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        aweme_id = aweme_item.get("aweme_id")
        # 笔记 urls 列表，若为短视频类型则返回为空列表
        note_download_url: List[str] = douyin_store._extract_note_image_list(aweme_item)

        if not note_download_url:
            return
        picNum = 0
        for url in note_download_url:
            if not url:
                continue
            content = await self.dy_client.get_aweme_media(url)
            await asyncio.sleep(random.random())
            if content is None:
                continue
            extension_file_name = f"{picNum:>03d}.jpeg"
            picNum += 1
            await douyin_store.update_dy_aweme_image(aweme_id, content, extension_file_name)

    async def get_aweme_video(self, aweme_item: Dict):
        """
        get aweme videos. please use get_aweme_media

        Args:
            aweme_item (Dict): 抖音作品详情
        """
        if not config.ENABLE_GET_MEIDAS:
            return
        aweme_id = aweme_item.get("aweme_id")

        # 视频 url，永远存在，但为短视频类型时的文件其实是音频文件
        video_download_url: str = douyin_store._extract_video_download_url(aweme_item)

        if not video_download_url:
            return
        content = await self.dy_client.get_aweme_media(video_download_url)
        await asyncio.sleep(random.random())
        if content is None:
            return
        extension_file_name = f"video.mp4"
        await douyin_store.update_dy_aweme_video(aweme_id, content, extension_file_name)
