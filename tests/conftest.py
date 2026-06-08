"""Shared pytest fixtures."""

import asyncio

import pytest


@pytest.fixture(scope="session")
def chromium_available():
    """Skip Playwright DOM tests when Chromium cannot launch (CI without browsers)."""
    pytest.importorskip("playwright.async_api")
    from playwright.async_api import async_playwright

    async def probe():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            await browser.close()

    try:
        asyncio.run(probe())
    except Exception as exc:
        pytest.skip(f"Chromium not launchable ({exc}). Install with: playwright install chromium")
    return True
