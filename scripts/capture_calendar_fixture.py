#!/usr/bin/env python3
"""Capture live calendar table HTML into tests/fixtures/ (run from repo root)."""

import argparse
import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app_logging import configure_logging

configure_logging()

from config_template import (  # noqa: E402
    KANAGAWA_TARGET_URL,
    TARGET_URL,
    HEADLESS,
    TIMEOUT,
)
from reservation_checker_playwright import ReservationChecker  # noqa: E402

FIXTURE_MAP = {
    'tokyo': (TARGET_URL, REPO_ROOT / 'tests/fixtures/tokyo_calendar_sample.html'),
    'kanagawa': (KANAGAWA_TARGET_URL, REPO_ROOT / 'tests/fixtures/kanagawa_calendar_sample.html'),
}


async def capture(source: str, outfile: Path) -> None:
    from playwright.async_api import async_playwright

    url = FIXTURE_MAP[source][0]
    checker = ReservationChecker(target_url=url, source_name=source)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_extra_http_headers({
            'User-Agent': (
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ),
        })
        await page.goto(url, timeout=TIMEOUT)
        await checker.wait_for_page_load(page)

        table = await page.query_selector('table#TBL, table.time--table, table')
        if not table:
            await browser.close()
            raise RuntimeError('No calendar table found on page')

        html = await table.evaluate('el => el.outerHTML')
        outfile.parent.mkdir(parents=True, exist_ok=True)
        outfile.write_text(html.strip() + '\n', encoding='utf-8')
        await browser.close()

    print(f'Wrote {len(html)} bytes to {outfile}')


def main():
    parser = argparse.ArgumentParser(description='Capture calendar HTML fixture')
    parser.add_argument(
        'source',
        choices=sorted(FIXTURE_MAP),
        help='tokyo or kanagawa',
    )
    args = parser.parse_args()
    _, path = FIXTURE_MAP[args.source]
    asyncio.run(capture(args.source, path))


if __name__ == '__main__':
    main()
