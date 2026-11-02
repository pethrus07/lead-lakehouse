"""Pool de browser Playwright com anti-detecção básica e atrasos randomizados."""

from __future__ import annotations

import asyncio
import random

from ..config import settings

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

_STEALTH = "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"


async def atraso() -> None:
    """Pausa aleatória entre as ações (evita padrão robótico)."""
    ms = random.randint(settings.delay_min_ms, settings.delay_max_ms)
    await asyncio.sleep(ms / 1000)


class BrowserPool:
    """Context manager assíncrono que abre um Chromium e serve páginas furtivas."""

    def __init__(self, headless: bool | None = None, proxy: str | None = None):
        self.headless = settings.headless if headless is None else headless
        self.proxy = proxy if proxy is not None else (settings.proxy_url or None)
        self._pw = None
        self._browser = None

    async def __aenter__(self) -> BrowserPool:
        from playwright.async_api import async_playwright

        self._pw = await async_playwright().start()
        kwargs: dict = {
            "headless": self.headless,
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        }
        if self.proxy:
            kwargs["proxy"] = {"server": self.proxy}
        self._browser = await self._pw.chromium.launch(**kwargs)
        return self

    async def nova_pagina(self):
        ctx = await self._browser.new_context(
            user_agent=random.choice(_USER_AGENTS),
            viewport={"width": 1366, "height": 900},
            locale="pt-BR",
        )
        await ctx.add_init_script(_STEALTH)
        return await ctx.new_page()

    async def __aexit__(self, *exc) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
