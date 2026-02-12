# -*- coding: utf-8 -*-
# 快手爬虫 - 独立版 (从 MediaCrawler 移植)
# 仅供学习和研究使用，请遵守平台使用条款

import sys
import io

# Force UTF-8 encoding
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'buffer'):
    if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import config

# 延迟导入：重型依赖在函数内部导入，使 --help 无需安装所有依赖即可运行
crawler = None


async def _generate_wordcloud_if_needed() -> None:
    if config.SAVE_DATA_OPTION != "json" or not config.ENABLE_GET_WORDCLOUD:
        return
    try:
        from tools.async_file_writer import AsyncFileWriter
        from var import crawler_type_var
        file_writer = AsyncFileWriter(
            platform=config.PLATFORM,
            crawler_type=crawler_type_var.get(),
        )
        await file_writer.generate_wordcloud_from_comments()
    except Exception as e:
        print(f"[Main] Error generating wordcloud: {e}")


async def main() -> None:
    global crawler
    from media_platform.kuaishou import KuaishouCrawler
    crawler = KuaishouCrawler()
    await crawler.start()
    await _generate_wordcloud_if_needed()


async def async_cleanup() -> None:
    global crawler
    if crawler:
        if getattr(crawler, "cdp_manager", None):
            try:
                await crawler.cdp_manager.cleanup(force=True)
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    print(f"[Main] Error cleaning up CDP browser: {e}")
        elif getattr(crawler, "browser_context", None):
            try:
                await crawler.browser_context.close()
            except Exception as e:
                error_msg = str(e).lower()
                if "closed" not in error_msg and "disconnected" not in error_msg:
                    print(f"[Main] Error closing browser context: {e}")


if __name__ == "__main__":
    from cli import parse_args

    args = parse_args()           # 解析 CLI 参数
    config.load_from_toml()       # 加载 TOML 配置（覆盖默认值）
    if args is not None:
        config.apply_cli_args(args)  # CLI 参数覆盖（最高优先级）

    from tools.app_runner import run

    def _force_stop() -> None:
        c = crawler
        if not c:
            return
        cdp_manager = getattr(c, "cdp_manager", None)
        launcher = getattr(cdp_manager, "launcher", None)
        if not launcher:
            return
        try:
            launcher.cleanup()
        except Exception:
            pass

    run(main, async_cleanup, cleanup_timeout_seconds=15.0, on_first_interrupt=_force_stop)
