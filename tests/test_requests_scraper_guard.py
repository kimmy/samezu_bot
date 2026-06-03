"""HTTP prototype must not notify without ALLOW_STANDALONE_NOTIFY=1."""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO_ROOT / 'scripts' / 'reservation_checker_requests.py'


def _load_requests_checker():
    spec = importlib.util.spec_from_file_location(
        'reservation_checker_requests', _SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules['reservation_checker_requests'] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_requests_run_check_does_not_notify_without_env(monkeypatch):
    mod = _load_requests_checker()
    monkeypatch.delenv('ALLOW_STANDALONE_NOTIFY', raising=False)
    checker = mod.ReservationChecker()
    checker.send_telegram_message = AsyncMock()
    checker._check_periods = AsyncMock(
        return_value=[{'date': '06/01', 'facility': '鮫洲試験場', 'applicant_type': '住民票のある方'}]
    )

    await checker.run_check(send_notifications=True)

    checker.send_telegram_message.assert_not_called()


@pytest.mark.asyncio
async def test_requests_run_check_notifies_with_env(monkeypatch):
    mod = _load_requests_checker()
    monkeypatch.setenv('ALLOW_STANDALONE_NOTIFY', '1')
    checker = mod.ReservationChecker()
    checker.send_telegram_message = AsyncMock()
    checker._check_periods = AsyncMock(
        return_value=[{'date': '06/01', 'facility': '鮫洲試験場', 'applicant_type': '住民票のある方'}]
    )

    await checker.run_check(send_notifications=True)

    checker.send_telegram_message.assert_called_once()
