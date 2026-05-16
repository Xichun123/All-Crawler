# -*- coding: utf-8 -*-
import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from playwright.async_api import async_playwright


VIDEO_PATTERN = re.compile(r"/video/(\d+)")


def dedupe(items: List[Dict]) -> List[Dict]:
    seen = set()
    result = []
    for item in items:
        video_id = item.get("video_id")
        if not video_id or video_id in seen:
            continue
        seen.add(video_id)
        result.append(item)
    return result


async def collect_visible_videos(page) -> List[Dict]:
    return await page.evaluate(
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
            const rect = a.getBoundingClientRect();
            return {
                video_id: match ? match[1] : "",
                aweme_id: match ? match[1] : "",
                video_url: href,
                title: textParts[0] || "",
                x: Math.round(rect.x),
                y: Math.round(rect.y)
            };
        })"""
    )


async def click_creator_search(page, keyword: str) -> None:
    box = await page.evaluate(
        """() => {
            const nodes = [...document.querySelectorAll('button, div, span, a')];
            const target = nodes
                .map((el) => ({ el, rect: el.getBoundingClientRect(), text: (el.innerText || el.getAttribute('aria-label') || '').trim() }))
                .filter((x) => x.rect.width > 0 && x.rect.height > 0)
                .filter((x) => x.rect.y > 240 && /??\\s*Ta\\s*???|??TA???|??.*??/.test(x.text))
                .sort((a, b) => (b.rect.width * b.rect.height) - (a.rect.width * a.rect.height))[0];
            if (!target) return null;
            return {
                x: target.rect.left + target.rect.width / 2,
                y: target.rect.top + target.rect.height / 2
            };
        }"""
    )
    if box:
        await page.mouse.click(box["x"], box["y"])
    else:
        # Current desktop layout: account-internal search is in the works toolbar.
        await page.mouse.click(1248, 300)
    await page.wait_for_timeout(800)
    await page.mouse.click(1248, 300)
    await page.wait_for_timeout(800)
    try:
        search_input = page.locator('input[placeholder*="??"], textarea[placeholder*="??"], [contenteditable="true"]').last
        await search_input.click(timeout=1500)
        await page.keyboard.press("Control+A")
    except Exception:
        pass
    await page.keyboard.type(keyword, delay=80)
    await page.keyboard.press("Enter")
    await page.wait_for_timeout(5000)


async def scrape(url: str, keyword: str, count: int, headless: bool) -> Dict:
    root = Path.cwd()
    user_data_dir = root / "browser_data" / "dy_user_data_dir"
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            channel="msedge",
            headless=headless,
            viewport={"width": 1440, "height": 1200},
            accept_downloads=False,
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        await click_creator_search(page, keyword)
        await page.screenshot(path=f"data/douyin/creator_search_after_{keyword}.png", full_page=False)

        all_items: List[Dict] = []
        stable_rounds = 0
        last_count = 0

        for _ in range(160):
            all_items = dedupe(all_items + await collect_visible_videos(page))
            print(f"collected={len(all_items)} url={page.url}", flush=True)
            if len(all_items) >= count:
                break

            if len(all_items) == last_count:
                stable_rounds += 1
            else:
                stable_rounds = 0
                last_count = len(all_items)
            if stable_rounds >= 15:
                break

            await page.mouse.wheel(0, 1800)
            await page.wait_for_timeout(1200)

        creator_name = ""
        try:
            creator_name = (await page.locator("h1").first.inner_text(timeout=2000)).strip()
        except Exception:
            pass

        final_url = page.url
        await context.close()

    return {
        "crawl_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "crawl_mode": "creator_search_page_browser",
        "source_url": url,
        "final_url": final_url,
        "keyword": keyword,
        "target_count": count,
        "actual_count": len(all_items[:count]),
        "creator": {"nickname": creator_name},
        "videos": all_items[:count],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("keyword")
    parser.add_argument("-n", "--count", type=int, default=80)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    data = asyncio.run(scrape(args.url, args.keyword, args.count, args.headless))
    out_dir = Path.cwd() / "data" / "douyin"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"creator_search_{args.keyword}_{timestamp}_{data['actual_count']}_videos.json"
    out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_file))
    print(f"actual_count={data['actual_count']}")


if __name__ == "__main__":
    main()
