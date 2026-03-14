"""
Playwright 浏览器搜索模块。
在真实浏览器环境中执行抖音搜索，彻底绕过 verify_check。
"""

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


# stealth 脚本：隐藏 webdriver 标识，防止被检测为自动化工具
STEALTH_JS = """
// 覆盖 navigator.webdriver 属性
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// 覆盖 chrome runtime 检测
window.chrome = { runtime: {} };

// 覆盖 permissions 查询
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
  parameters.name === 'notifications'
    ? Promise.resolve({ state: Notification.permission })
    : originalQuery(parameters);

// 覆盖 plugins 长度
Object.defineProperty(navigator, 'plugins', {
  get: () => [1, 2, 3, 4, 5],
});

// 覆盖 languages
Object.defineProperty(navigator, 'languages', {
  get: () => ['zh-CN', 'zh', 'en'],
});
"""


class BrowserSearchProvider:
    """使用 Playwright 浏览器执行抖音搜索的 Provider。"""

    def __init__(self, cookie_path: str = ""):
        self._cookie_path = cookie_path or os.path.expanduser(
            "~/.config/douyinmcp/cookies.txt"
        )
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._launched = False

    async def launch(self) -> None:
        """启动浏览器并加载 Cookie。"""
        if self._launched:
            return

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        # 创建浏览器上下文
        self._context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/135.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
        )

        # 注入 stealth 脚本
        await self._context.add_init_script(STEALTH_JS)

        # 加载 Cookie
        await self._load_cookies()

        # 创建页面并访问抖音首页
        self._page = await self._context.new_page()
        await self._page.goto("https://www.douyin.com/", wait_until="domcontentloaded", timeout=30000)
        # 等待页面加载完成
        await asyncio.sleep(3)

        self._launched = True

    async def _load_cookies(self) -> None:
        """从文件加载 Cookie 到浏览器上下文。"""
        if not os.path.exists(self._cookie_path):
            return

        with open(self._cookie_path, "r") as f:
            cookie_str = f.read().strip()

        cookies = []
        for part in cookie_str.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            name, value = part.split("=", 1)
            name = name.strip()
            value = value.strip()
            if name and value:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".douyin.com",
                    "path": "/",
                })

        if cookies:
            await self._context.add_cookies(cookies)

    async def search(self, keyword: str, count: int = 10) -> Dict[str, Any]:
        """
        在浏览器中执行搜索并通过网络拦截获取API响应。

        核心策略：导航到搜索页后，浏览器会自动发出搜索API请求，
        我们监听这个请求的响应，直接获取JSON数据。

        Args:
            keyword: 搜索关键词
            count: 期望结果数量

        Returns:
            包含搜索结果的字典
        """
        if not self._launched:
            await self.launch()

        # 用于存储拦截到的搜索API响应
        captured_data: List[Dict] = []

        async def on_response(response):
            """监听搜索API响应"""
            url = response.url
            if "/aweme/v1/web/general/search" in url:
                try:
                    body = await response.json()
                    if body.get("data"):
                        captured_data.append(body)
                except Exception:
                    pass

        # 注册响应监听器
        self._page.on("response", on_response)

        try:
            # 导航到搜索页面（浏览器会自动发出搜索API请求）
            from urllib.parse import quote
            search_url = f"https://www.douyin.com/search/{quote(keyword)}?type=general"
            await self._page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

            # 等待搜索API响应被捕获（最多15秒）
            for _ in range(30):
                if captured_data:
                    break
                await asyncio.sleep(0.5)

            # 如果没有自动触发，可能需要等待更久
            if not captured_data:
                await asyncio.sleep(5)

        finally:
            # 移除监听器
            self._page.remove_listener("response", on_response)

        # 解析捕获的数据
        results = []
        if captured_data:
            api_data = captured_data[0]
            for item in api_data.get("data", [])[:count]:
                aweme = item.get("aweme_info") or item
                if not aweme.get("aweme_id"):
                    continue
                results.append({
                    "aweme_id": aweme.get("aweme_id", ""),
                    "title": aweme.get("desc", ""),
                    "author": aweme.get("author", {}).get("nickname", ""),
                    "sec_uid": aweme.get("author", {}).get("sec_uid", ""),
                    "likes": aweme.get("statistics", {}).get("digg_count", 0),
                    "comments": aweme.get("statistics", {}).get("comment_count", 0),
                    "shares": aweme.get("statistics", {}).get("share_count", 0),
                    "source": "browser_api_intercept",
                })

        return {
            "success": True,
            "keyword": keyword,
            "count": len(results),
            "has_more": captured_data[0].get("has_more", 0) if captured_data else 0,
            "results": results,
        }

    async def close(self) -> None:
        """关闭浏览器。"""
        if self._page:
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._launched = False


# 全局单例
_provider: Optional[BrowserSearchProvider] = None


async def get_browser_search_provider() -> BrowserSearchProvider:
    """获取或创建浏览器搜索 Provider 单例。"""
    global _provider
    if _provider is None:
        _provider = BrowserSearchProvider()
    return _provider
