"""Regression tests for wait queues and scrape locking."""

import asyncio
import time
import unittest.mock as mock

import pytest
from run_bot import SamezuBot
from tests.test_helpers import (
    CHECK_KANAGAWA,
    CHECK_SAITAMA,
    CHECK_TOKYO_BOTH,
    CHECK_TOKYO_MIXED,
    check_error,
    check_from_slots,
)

TOKYO_RESULT = check_from_slots(
    [{"date": "06/05 (Thu)", "facility": "鮫洲試験場", "applicant_type": "住民票のある方"}],
    facilities_label=["鮫洲試験場", "府中試験場"],
)
KANAGAWA_RESULT = CHECK_KANAGAWA
SAITAMA_RESULT = CHECK_SAITAMA


def make_bot():
    return SamezuBot()


def test_scrape_key_maps_samezu_and_fuchu_to_tokyo():
    bot = make_bot()
    assert bot._scrape_key_for_check("samezu") == "tokyo"
    assert bot._scrape_key_for_check("fuchu") == "tokyo"
    assert bot._scrape_key_for_check(None) == "tokyo"
    assert bot._scrape_key_for_check("kanagawa") == "kanagawa"
    assert bot._scrape_key_for_check("saitama") == "saitama"


@pytest.mark.asyncio
async def test_deliver_to_waiting_users_applies_per_user_check_source():
    bot = make_bot()
    bot._update_cache_after_scrape(bot.cache, CHECK_TOKYO_BOTH, use_month_navigation=False)
    sent = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        sent.append((chat_id, text))

    bot._telegram_send = capture_send
    bot.waiting_users["tokyo"].add((1, 101, "samezu", False, False, False))
    bot.waiting_users["tokyo"].add((2, 102, "fuchu", False, False, False))

    await bot._deliver_to_waiting_users("tokyo", from_fresh_scrape=True)

    assert len(sent) == 2
    by_chat = {chat_id: text for chat_id, text in sent}
    assert "🏢 <b>鮫洲試験場</b>" in by_chat[101]
    assert "🏢 <b>府中試験場</b>" not in by_chat[101]
    assert "🏢 <b>府中試験場</b>" in by_chat[102]
    assert "🏢 <b>鮫洲試験場</b>" not in by_chat[102]


@pytest.mark.asyncio
async def test_month_waiter_not_served_from_weekly_fresh_cache():
    bot = make_bot()
    bot._update_cache_after_scrape(bot.cache, TOKYO_RESULT, use_month_navigation=False)
    sent = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        sent.append(chat_id)

    bot._telegram_send = capture_send
    bot.waiting_users["tokyo"].add((1, 100, None, False, True, False))

    await bot._deliver_to_waiting_users("tokyo", from_fresh_scrape=True)

    assert sent == []
    assert len(bot.waiting_users["tokyo"]) == 1


@pytest.mark.asyncio
async def test_force_waiter_not_served_from_stale_other_key_cache():
    bot = make_bot()
    bot.kanagawa_cache['result'] = KANAGAWA_RESULT
    bot.kanagawa_cache['timestamp'] = time.time() - 9999
    bot.kanagawa_cache['use_month_navigation'] = False
    sent = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        sent.append(chat_id)

    bot._telegram_send = capture_send
    bot.waiting_users["kanagawa"].add((2, 200, "kanagawa", False, False, True))

    await bot._deliver_to_waiting_users("kanagawa", from_fresh_scrape=False)

    assert sent == []
    assert len(bot.waiting_users["kanagawa"]) == 1


@pytest.mark.asyncio
async def test_force_waiter_not_served_from_stale_saitama_cache():
    bot = make_bot()
    bot.saitama_cache['result'] = SAITAMA_RESULT
    bot.saitama_cache['timestamp'] = time.time() - 9999
    bot.saitama_cache['use_month_navigation'] = False
    sent = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        sent.append(chat_id)

    bot._telegram_send = capture_send
    bot.waiting_users["saitama"].add((2, 200, "saitama", False, False, True))

    await bot._deliver_to_waiting_users("saitama", from_fresh_scrape=False)

    assert sent == []
    assert len(bot.waiting_users["saitama"]) == 1


@pytest.mark.asyncio
async def test_other_key_waiters_served_from_valid_matching_cache():
    bot = make_bot()
    messages = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        messages.append((chat_id, text))

    bot._telegram_send = capture_send
    bot._update_cache_after_scrape(bot.kanagawa_cache, KANAGAWA_RESULT, use_month_navigation=False)
    bot._update_cache_after_scrape(bot.saitama_cache, SAITAMA_RESULT, use_month_navigation=False)

    async def fake_run_check(*args, **kwargs):
        return TOKYO_RESULT

    bot.reservation_checker.run_check = fake_run_check
    bot.waiting_users["tokyo"].add((1, 100, None, False, False, False))
    bot.waiting_users["kanagawa"].add((2, 200, "kanagawa", False, False, False))
    bot.waiting_users["saitama"].add((3, 300, "saitama", False, False, False))

    await bot._background_check_task(None, source=None, scrape_key="tokyo")

    assert len(messages) == 3
    by_chat = {chat_id: text for chat_id, text in messages}
    assert "鮫洲試験場" in by_chat[100]
    assert "普通車ＡＭ" in by_chat[200]
    assert "【１】１回目（初めて）" in by_chat[300]
    assert not bot.waiting_users["kanagawa"]
    assert not bot.waiting_users["saitama"]


@pytest.mark.asyncio
async def test_chained_scrape_starts_for_waiters_without_cache():
    bot = make_bot()
    bot.waiting_users["kanagawa"].add((2, 200, "kanagawa", True, True, False))
    created = []

    def fake_create_task(coro):
        coro.close()
        created.append(1)
        return mock.MagicMock()

    with mock.patch('run_bot.asyncio.create_task', side_effect=fake_create_task):
        await bot._start_chained_scrapes_for_remaining_waiters()

    assert len(created) == 1


@pytest.mark.asyncio
async def test_deliver_respects_show_all_for_queued_user():
    bot = make_bot()
    bot._update_cache_after_scrape(bot.cache, CHECK_TOKYO_MIXED, use_month_navigation=False)
    sent = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        sent.append(text)

    bot._telegram_send = capture_send
    bot.waiting_users["tokyo"].add((1, 100, None, True, False, False))

    await bot._deliver_to_waiting_users("tokyo", from_fresh_scrape=True)

    assert len(sent) == 1
    assert '住民票のない方' in sent[0]


@pytest.mark.asyncio
async def test_concurrent_reserve_only_starts_one_background_scrape():
    bot = make_bot()
    run_count = 0

    async def slow_run_check(*args, **kwargs):
        nonlocal run_count
        run_count += 1
        await asyncio.sleep(0.05)
        return "❌ No slots"

    bot.reservation_checker.run_check = slow_run_check

    reserved = await asyncio.gather(
        bot._reserve_and_start_background_check(
            None, use_month_navigation=False, show_all=False, source=None, scrape_key="tokyo"
        ),
        bot._reserve_and_start_background_check(
            None, use_month_navigation=False, show_all=False, source=None, scrape_key="tokyo"
        ),
    )
    await asyncio.sleep(0.2)

    assert sum(reserved) == 1
    assert run_count == 1


@pytest.mark.asyncio
async def test_error_scrape_requeues_incompatible_month_waiter():
    bot = make_bot()
    sent = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        sent.append((chat_id, text))

    async def fail_weekly(*args, **kwargs):
        return check_error("❌ Error during reservation check: timeout")

    bot._telegram_send = capture_send
    bot.reservation_checker.run_check = fail_weekly
    bot.waiting_users["tokyo"].add((1, 100, None, False, False, False))
    bot.waiting_users["tokyo"].add((2, 200, None, False, True, False))

    await bot._background_check_task(None, use_month_navigation=False, scrape_key="tokyo")

    assert len(sent) == 1
    assert sent[0][0] == 100
    assert "timeout" in sent[0][1]
    assert len(bot.waiting_users["tokyo"]) == 1
    assert next(iter(bot.waiting_users["tokyo"]))[4] is True


@pytest.mark.asyncio
async def test_exception_scrape_requeues_incompatible_month_waiter():
    bot = make_bot()
    sent = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        sent.append((chat_id, text))

    async def explode(*args, **kwargs):
        raise RuntimeError("browser died")

    bot._telegram_send = capture_send
    bot.reservation_checker.run_check = explode
    bot.waiting_users["tokyo"].add((1, 100, None, False, False, False))
    bot.waiting_users["tokyo"].add((2, 200, None, False, True, False))

    await bot._background_check_task(None, use_month_navigation=False, scrape_key="tokyo")

    assert len(sent) == 1
    assert sent[0][0] == 100
    assert "browser died" in sent[0][1]
    assert len(bot.waiting_users["tokyo"]) == 1


@pytest.mark.asyncio
async def test_scheduler_skips_when_check_lock_held():
    bot = SamezuBot()
    scrape_calls = []

    async def fake_run_check(*args, **kwargs):
        scrape_calls.append(kwargs.get("source") or "check")
        return "❌ No slots"

    bot.reservation_checker.run_check = fake_run_check
    bot.kanagawa_checker.run_check = fake_run_check
    bot.saitama_checker.run_check = fake_run_check

    await bot.check_lock.acquire()

    call_count = 0

    async def fast_sleep(_):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise asyncio.CancelledError()

    with mock.patch('asyncio.sleep', fast_sleep):
        task = asyncio.create_task(bot._scheduler_loop())
        try:
            await task
        except asyncio.CancelledError:
            pass

    bot.check_lock.release()

    assert scrape_calls == []
