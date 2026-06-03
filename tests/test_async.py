import pytest
import asyncio
import unittest.mock as mock
from run_bot import SamezuBot

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
        if call_count >= 2:
            raise asyncio.CancelledError()

    async def fake_run_check(*args, **kwargs):
        return run_check_result

    notifications_sent = []

    async def fake_send_notifications(result, source=None):
        notifications_sent.append(result)

    bot.reservation_checker.run_check = fake_run_check
    bot.kanagawa_checker.run_check = fake_run_check
    bot._send_notifications_to_subscribers = fake_send_notifications

    with mock.patch('asyncio.sleep', fast_sleep):
        task = asyncio.create_task(bot._scheduler_loop())
        try:
            await task
        except asyncio.CancelledError:
            pass

    return notifications_sent


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_on_error():
    bot = SamezuBot()
    error_result = "❌ Error during reservation check: HTTPSConnectionPool(host='example.com', port=443): Read timed out."
    notifications_sent = await _run_one_scheduler_iteration(bot, error_result)
    assert notifications_sent == [], "Scheduler should not notify subscribers on error"


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_on_no_slots():
    bot = SamezuBot()
    notifications_sent = await _run_one_scheduler_iteration(bot, "❌ No slots")
    assert notifications_sent == [], "Scheduler should not notify subscribers when no slots found"


@pytest.mark.asyncio
async def test_scheduler_notifies_on_slots_found():
    bot = SamezuBot()
    slots_result = "🎉 <b>Available Reservation Slots Found!</b>\n\n📅 <b>2026-03-20</b>\n   🏢 <b>鮫洲試験場</b>\n      • 住民票のある方\n"
    notifications_sent = await _run_one_scheduler_iteration(bot, slots_result)
    # Two checkers (tokyo + kanagawa) both return slots, so two notifications
    assert len(notifications_sent) >= 1, "Scheduler should notify subscribers when slots are found"
    assert all("🎉" in n for n in notifications_sent)


@pytest.mark.asyncio
async def test_scheduler_does_not_notify_duplicate():
    bot = SamezuBot()
    slots_result = "🎉 <b>Available Reservation Slots Found!</b>\n\n📅 <b>2026-03-20</b>\n   🏢 <b>鮫洲試験場</b>\n      • 住民票のある方\n"
    # First iteration — should notify
    await _run_one_scheduler_iteration(bot, slots_result)
    # Second iteration with identical result — should not notify again
    notifications_sent = await _run_one_scheduler_iteration(bot, slots_result)
    assert notifications_sent == [], "Scheduler should not re-notify when slots are unchanged"


@pytest.mark.asyncio
async def test_scheduler_notifies_again_after_slots_clear_and_reappear():
    bot = SamezuBot()
    slots_result = "🎉 <b>Available Reservation Slots Found!</b>\n\n📅 <b>2026-03-20</b>\n   🏢 <b>鮫洲試験場</b>\n      • 住民票のある方\n"
    no_slots = "❌ No slots"
    await _run_one_scheduler_iteration(bot, slots_result)  # first notification
    await _run_one_scheduler_iteration(bot, no_slots)       # slots gone — resets last_notified
    notifications_sent = await _run_one_scheduler_iteration(bot, slots_result)  # same slots reappear
    assert len(notifications_sent) >= 1, "Should notify again after slots cleared and reappeared"
