"""Optional live-site Playwright smoke (off by default; not run in deploy pytest)."""

import os

import pytest

pytest.importorskip("playwright.async_api")

from config_template import (
    KANAGAWA_TARGET_FACILITIES,
    KANAGAWA_TARGET_SLOT_TYPES,
    KANAGAWA_TARGET_URL,
    SAITAMA_TARGET_FACILITIES,
    SAITAMA_TARGET_SLOT_TYPES,
    SAITAMA_TARGET_URL,
    TARGET_FACILITIES,
    TARGET_SLOT_TYPES,
    TARGET_URL,
)
from domain import format_check_message
from reservation_checker_playwright import ReservationChecker

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_live_tokyo_scrape_returns_check_result():
    if not os.environ.get("LIVE_SCRAPE"):
        pytest.skip("Set LIVE_SCRAPE=1 to hit the reservation websites")

    checker = ReservationChecker(
        target_url=TARGET_URL,
        target_facilities=TARGET_FACILITIES,
        target_slot_types=TARGET_SLOT_TYPES,
        source_name="tokyo",
    )
    check = await checker.run_check(send_notifications=False, show_all=True)
    assert check.is_error or isinstance(format_check_message(check), str)


@pytest.mark.asyncio
async def test_live_saitama_scrape_returns_check_result():
    if not os.environ.get("LIVE_SCRAPE"):
        pytest.skip("Set LIVE_SCRAPE=1 to hit the reservation websites")

    checker = ReservationChecker(
        target_url=SAITAMA_TARGET_URL,
        target_facilities=SAITAMA_TARGET_FACILITIES,
        target_slot_types=SAITAMA_TARGET_SLOT_TYPES,
        source_name="saitama",
    )
    check = await checker.run_check(send_notifications=False, show_all=True)
    assert check.is_error or isinstance(format_check_message(check), str)
