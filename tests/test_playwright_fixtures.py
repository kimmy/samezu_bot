"""Playwright parses saved calendar HTML (no live site; exercises real DOM selectors)."""

from pathlib import Path

import pytest

pytest.importorskip("playwright.async_api")

from playwright.async_api import async_playwright

pytestmark = pytest.mark.usefixtures("chromium_available")

from config_template import (
    KANAGAWA_TARGET_FACILITIES,
    KANAGAWA_TARGET_SLOT_TYPES,
    SAITAMA_TARGET_FACILITIES,
    TARGET_FACILITIES,
)
from reservation_checker_playwright import ReservationChecker

FIXTURES = Path(__file__).parent / "fixtures"


async def _slots_from_fixture_html(checker: ReservationChecker, html: str):
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.set_content(html, wait_until="domcontentloaded")
            return await checker.get_available_dates(page)
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_playwright_parses_kanagawa_fixture_including_pm_rowspan():
    checker = ReservationChecker(
        target_facilities=KANAGAWA_TARGET_FACILITIES,
        target_slot_types=KANAGAWA_TARGET_SLOT_TYPES,
        source_name="kanagawa",
    )
    html = (FIXTURES / "kanagawa_calendar_sample.html").read_text(encoding="utf-8")
    slots = await _slots_from_fixture_html(checker, html)

    assert len(slots) == 3
    am = [s for s in slots if s.applicant_type == "普通車ＡＭ"]
    pm = [s for s in slots if s.applicant_type == "普通車ＰＭ"]
    assert len(am) == 1 and "08/14" in am[0].date
    assert len(pm) == 2
    assert all(s.facility == "外国免許四輪車" for s in slots)


@pytest.mark.asyncio
async def test_playwright_parses_saitama_fixture_including_rowspan():
    checker = ReservationChecker(
        target_facilities=SAITAMA_TARGET_FACILITIES,
        target_slot_types=[],
        source_name="saitama",
    )
    html = (FIXTURES / "saitama_calendar_sample.html").read_text(encoding="utf-8")
    slots = await _slots_from_fixture_html(checker, html)

    assert len(slots) == 3
    by_type = {s.applicant_type: s for s in slots}
    assert set(by_type) == {"【１】１回目（初めて）", "【２】２回目以降", "【３】免除国等"}
    assert "08/26" in by_type["【１】１回目（初めて）"].date
    assert "08/27" in by_type["【２】２回目以降"].date
    assert "08/27" in by_type["【３】免除国等"].date
    assert all(s.facility == "外免　書類審査" for s in slots)


@pytest.mark.asyncio
async def test_playwright_parses_tokyo_fixture_open_slot():
    checker = ReservationChecker(
        target_facilities=TARGET_FACILITIES,
        target_slot_types=[],
        source_name="tokyo",
    )
    html = (FIXTURES / "tokyo_calendar_sample.html").read_text(encoding="utf-8")
    slots = await _slots_from_fixture_html(checker, html)

    assert len(slots) == 1
    assert slots[0].facility == "鮫洲試験場"
    assert slots[0].applicant_type == "29の国･地域以外の方で、住民票のない方"
    assert "08/21" in slots[0].date
