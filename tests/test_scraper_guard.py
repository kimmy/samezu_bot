"""Standalone scraper must not broadcast without ALLOW_STANDALONE_NOTIFY=1."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reservation_checker_playwright import ReservationChecker

SAMPLE_SLOT = {"date": "06/01", "facility": "鮫洲試験場", "applicant_type": "住民票のある方"}


def _playwright_patches():
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.title = AsyncMock(return_value="Calendar")
    mock_page.url = "https://example.com"
    mock_page.wait_for_timeout = AsyncMock()

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.route = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_pw = MagicMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw.__aexit__ = AsyncMock(return_value=None)

    return patch("reservation_checker_playwright.async_playwright", return_value=mock_pw)


@pytest.mark.asyncio
async def test_run_check_does_not_notify_without_env(monkeypatch):
    monkeypatch.delenv("ALLOW_STANDALONE_NOTIFY", raising=False)
    checker = ReservationChecker()
    sent = []
    checker.send_telegram_message = AsyncMock(side_effect=lambda m: sent.append(m))
    checker.check_all_weeks = AsyncMock(return_value=[SAMPLE_SLOT])

    with _playwright_patches(), patch.object(checker, "wait_for_page_load", AsyncMock()):
        await checker.run_check(send_notifications=True)

    checker.send_telegram_message.assert_not_called()
    assert sent == []


@pytest.mark.asyncio
async def test_run_check_notifies_when_env_opt_in(monkeypatch):
    monkeypatch.setenv("ALLOW_STANDALONE_NOTIFY", "1")
    checker = ReservationChecker()
    checker.send_telegram_message = AsyncMock()
    checker.check_all_weeks = AsyncMock(return_value=[SAMPLE_SLOT])

    with _playwright_patches(), patch.object(checker, "wait_for_page_load", AsyncMock()):
        await checker.run_check(send_notifications=True)

    checker.send_telegram_message.assert_called_once()
