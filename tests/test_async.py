import pytest
import asyncio
import unittest.mock as mock
from domain import format_check_message
from run_bot import SamezuBot
from tests.test_helpers import (
    CHECK_NO_SLOTS,
    CHECK_SAITAMA,
    CHECK_TOKYO_ARI,
    check_error,
    check_from_slots,
)

@pytest.mark.asyncio
async def test_subscribe_command(monkeypatch):
    bot = SamezuBot()
    # Mock get_subscribers to ensure user is not already subscribed
    bot.get_subscribers = lambda: []
    class DummyUser:
        id = 12345
        username = "testuser"
    class DummyMessage:
        async def reply_text(self, *args, **kwargs):
            return None
    class DummyUpdate:
        effective_chat = type('Chat', (), {'id': 12345})
        effective_user = DummyUser()
        message = DummyMessage()
    class DummyContext:
        DEFAULT_TYPE = None
        args = []  # Add missing args attribute
    called = {}

    def fake_upsert_subscriber(chat_id, user_info=None):
        called['chat_id'] = chat_id
        called['user_info'] = user_info

    bot.upsert_subscriber = fake_upsert_subscriber
    await bot.subscribe_command(DummyUpdate(), DummyContext())
    assert called['chat_id'] == 12345
    assert 'samezu' in called['user_info']


async def _run_one_scheduler_iteration(bot, run_check_result):
    """Run the scheduler loop for exactly one check iteration then cancel."""
    call_count = 0

    async def fast_sleep(_):
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            raise asyncio.CancelledError()

    async def fake_run_check(*args, **kwargs):
        return run_check_result

    notifications_sent = []

    async def fake_send_notifications(check, source=None):
        notifications_sent.append(format_check_message(check))

    bot.reservation_checker.run_check = fake_run_check
    bot.kanagawa_checker.run_check = fake_run_check
    bot.saitama_checker.run_check = fake_run_check
    bot._send_notifications_to_subscribers = fake_send_notifications

    with mock.patch('asyncio.sleep', fast_sleep):
        task = asyncio.create_task(bot._scheduler_loop())
        try:
            await task
        except asyncio.CancelledError:
            pass

    return notifications_sent


async def _run_one_scheduler_iteration_saitama(bot, saitama_result):
    """Isolate the Saitama scheduler result — tokyo/kanagawa report no slots."""
    call_count = 0

    async def fast_sleep(_):
        nonlocal call_count
        call_count += 1
        if call_count >= 1:
            raise asyncio.CancelledError()

    async def fake_no_slots(*args, **kwargs):
        return CHECK_NO_SLOTS

    async def fake_saitama(*args, **kwargs):
        return saitama_result

    notifications_sent = []

    async def fake_send_notifications(check, source=None):
        notifications_sent.append(format_check_message(check))

    bot.reservation_checker.run_check = fake_no_slots
    bot.kanagawa_checker.run_check = fake_no_slots
    bot.saitama_checker.run_check = fake_saitama
    bot._send_notifications_to_subscribers = fake_send_notifications

    with mock.patch('asyncio.sleep', fast_sleep):
        task = asyncio.create_task(bot._scheduler_loop())
        try:
            await task
        except asyncio.CancelledError:
            pass

    return notifications_sent


@pytest.mark.asyncio
async def test_scheduler_populates_cache_before_first_sleep():
    bot = SamezuBot()
    await _run_one_scheduler_iteration(bot, CHECK_NO_SLOTS)
    assert bot.cache['result'] == CHECK_NO_SLOTS
    assert bot.cache['timestamp'] is not None
    assert bot.kanagawa_cache['result'] == CHECK_NO_SLOTS
    assert bot.saitama_cache['result'] == CHECK_NO_SLOTS


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_on_error():
    bot = SamezuBot()
    error_result = check_error(
        "❌ Error during reservation check: HTTPSConnectionPool(host='example.com', port=443): Read timed out."
    )
    notifications_sent = await _run_one_scheduler_iteration(bot, error_result)
    assert notifications_sent == [], "Scheduler should not notify subscribers on error"


@pytest.mark.asyncio
async def test_scheduler_does_not_cache_error_result():
    bot = SamezuBot()
    good = check_from_slots(
        [{"date": "06/05 (Thu)", "facility": "鮫洲試験場", "applicant_type": "住民票のある方"}],
        facilities_label=["鮫洲試験場"],
    )
    bot._update_cache_after_scrape(bot.cache, good, use_month_navigation=False)
    prior_check = bot.cache['result']
    prior_ts = bot.cache['timestamp']

    async def fail_tokyo(*args, **kwargs):
        return check_error("❌ Error during reservation check: timeout")

    bot.reservation_checker.run_check = fail_tokyo
    await bot._run_scheduled_check(bot.reservation_checker, bot.cache, "tokyo")

    assert bot.cache['result'] is prior_check
    assert bot.cache['timestamp'] == prior_ts


@pytest.mark.asyncio
async def test_scheduler_preserves_last_notified_after_transient_error():
    bot = SamezuBot()
    await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)
    prior = bot.last_notified["tokyo"]
    assert prior is not None

    error_result = check_error("❌ Error during reservation check: timeout")
    await _run_one_scheduler_iteration(bot, error_result)
    assert bot.last_notified["tokyo"] == prior

    notifications_sent = await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)
    assert notifications_sent == [], "Same slots after error should not re-notify"


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_on_no_slots():
    bot = SamezuBot()
    notifications_sent = await _run_one_scheduler_iteration(bot, CHECK_NO_SLOTS)
    assert notifications_sent == [], "Scheduler should not notify subscribers when no slots found"


@pytest.mark.asyncio
async def test_scheduler_notifies_on_slots_found():
    bot = SamezuBot()
    notifications_sent = await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)
    # Two checkers (tokyo + kanagawa) both return slots, so two notifications
    assert len(notifications_sent) >= 1, "Scheduler should notify subscribers when slots are found"
    assert all("🎉" in n for n in notifications_sent)


def test_last_notified_loads_from_file(tmp_path, monkeypatch):
    path = tmp_path / "last_notified.json"
    path.write_text(
        '{"tokyo": [["06/05 (Thu)", "鮫洲試験場", "住民票のある方"]], "kanagawa": null}\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(SamezuBot, "LAST_NOTIFIED_FILE", str(path))
    bot = SamezuBot()
    assert bot.last_notified["tokyo"] == (
        ("06/05 (Thu)", "鮫洲試験場", "住民票のある方"),
    )
    assert bot.last_notified["kanagawa"] is None
    assert bot.last_notified["saitama"] is None  # missing key defaults to None, no migration needed


@pytest.mark.asyncio
async def test_last_notified_persisted_after_scheduler_notify(tmp_path, monkeypatch):
    path = tmp_path / "last_notified.json"
    monkeypatch.setattr(SamezuBot, "LAST_NOTIFIED_FILE", str(path))
    bot = SamezuBot()
    await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)

    assert path.exists()
    reloaded = SamezuBot()
    assert reloaded.last_notified["tokyo"] == bot.last_notified["tokyo"]
    assert reloaded.last_notified["tokyo"] is not None


@pytest.mark.asyncio
async def test_last_notified_cleared_in_file_when_slots_disappear(tmp_path, monkeypatch):
    path = tmp_path / "last_notified.json"
    monkeypatch.setattr(SamezuBot, "LAST_NOTIFIED_FILE", str(path))
    bot = SamezuBot()
    await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)
    await _run_one_scheduler_iteration(bot, CHECK_NO_SLOTS)

    reloaded = SamezuBot()
    assert reloaded.last_notified["tokyo"] is None


@pytest.mark.asyncio
async def test_scheduler_last_notified_stores_slot_signature():
    bot = SamezuBot()
    await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)
    assert isinstance(bot.last_notified["tokyo"], tuple)
    assert len(bot.last_notified["tokyo"]) >= 1


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_duplicate():
    bot = SamezuBot()
    # First iteration — should notify
    await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)
    # Second iteration with identical result — should not notify again
    notifications_sent = await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)
    assert notifications_sent == [], "Scheduler should not re-notify when slots are unchanged"


@pytest.mark.asyncio
async def test_scheduler_notifies_again_after_slots_clear_and_reappear():
    bot = SamezuBot()
    await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)  # first notification
    await _run_one_scheduler_iteration(bot, CHECK_NO_SLOTS)  # slots gone — resets last_notified
    notifications_sent = await _run_one_scheduler_iteration(bot, CHECK_TOKYO_ARI)  # same slots reappear
    assert len(notifications_sent) >= 1, "Should notify again after slots cleared and reappeared"


@pytest.mark.asyncio
async def test_scheduler_notifies_on_slots_found_saitama():
    bot = SamezuBot()
    notifications_sent = await _run_one_scheduler_iteration_saitama(bot, CHECK_SAITAMA)
    assert len(notifications_sent) == 1
    assert "🎉" in notifications_sent[0]
    assert "【１】１回目（初めて）" in notifications_sent[0]


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_duplicate_saitama():
    bot = SamezuBot()
    await _run_one_scheduler_iteration_saitama(bot, CHECK_SAITAMA)
    notifications_sent = await _run_one_scheduler_iteration_saitama(bot, CHECK_SAITAMA)
    assert notifications_sent == [], "Scheduler should not re-notify when Saitama slots are unchanged"


@pytest.mark.asyncio
async def test_scheduler_notifies_again_after_saitama_slots_clear_and_reappear():
    bot = SamezuBot()
    await _run_one_scheduler_iteration_saitama(bot, CHECK_SAITAMA)
    await _run_one_scheduler_iteration_saitama(bot, CHECK_NO_SLOTS)
    notifications_sent = await _run_one_scheduler_iteration_saitama(bot, CHECK_SAITAMA)
    assert len(notifications_sent) == 1, "Should notify again after Saitama slots cleared and reappeared"
