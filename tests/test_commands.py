class DummyApplication:
    def create_task(self, coro):
        return None
import pytest
import asyncio
from run_bot import SamezuBot
from tests.test_helpers import CHECK_KANAGAWA, CHECK_SAITAMA, check_error, check_from_slots

TOKYO_RESULT = check_from_slots(
    [{"date": "06/05 (Thu)", "facility": "鮫洲試験場", "applicant_type": "住民票のある方"}],
    facilities_label=["鮫洲試験場"],
)
KANAGAWA_RESULT = CHECK_KANAGAWA
SAITAMA_RESULT = CHECK_SAITAMA

class DummyUser:
    id = 12345
    username = "testuser"
    first_name = "Test"
    last_name = "User"

class DummyMessage:
    def __init__(self):
        self.last_text = None
    async def reply_text(self, text, **kwargs):
        self.last_text = text
        return text

class DummyChat:
    id = 12345

class DummyUpdate:
    effective_chat = DummyChat()
    effective_user = DummyUser()
    message = DummyMessage()

class DummyContext:
    DEFAULT_TYPE = None
    args = []
    bot = None

@pytest.mark.asyncio
async def test_check_does_not_serve_cached_error():
    bot = SamezuBot()
    update = DummyUpdate()
    import time

    bot.cache['result'] = check_error("❌ Error during reservation check: timeout")
    bot.cache['timestamp'] = time.time()

    handled = await bot._handle_cached_result(
        update,
        "testuser",
        12345,
        force_check=False,
        show_all=False,
        cache=bot.cache,
        checker=bot.reservation_checker,
    )
    assert handled is False


@pytest.mark.asyncio
async def test_check_command_cache_valid():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    import time
    bot._update_cache_after_scrape(bot.cache, TOKYO_RESULT, use_month_navigation=False)
    await bot.check_command(update, context)
    assert "Using cached result" in update.message.last_text

@pytest.mark.asyncio
async def test_check_command_cache_expired():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot.cache['result'] = None
    bot.cache['timestamp'] = None
    bot.application = DummyApplication()
    bot.check_lock = asyncio.Lock()
    await bot.check_command(update, context)
    assert "Checking for available slots" in update.message.last_text

@pytest.mark.asyncio
async def test_check_command_force():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    context.args = ["force"]
    import time
    bot.cache['result'] = TOKYO_RESULT
    bot.cache['timestamp'] = time.time()
    bot.application = DummyApplication()
    bot.check_lock = asyncio.Lock()
    await bot.check_command(update, context)
    assert "Checking for available slots" in update.message.last_text

@pytest.mark.asyncio
async def test_check_month_command_cache_valid():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot._update_cache_after_scrape(bot.cache, TOKYO_RESULT, use_month_navigation=True)
    await bot.check_month_command(update, context)
    assert "Using cached result" in update.message.last_text


@pytest.mark.asyncio
async def test_check_month_rejects_weekly_cache():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot._update_cache_after_scrape(bot.cache, TOKYO_RESULT, use_month_navigation=False)
    bot.application = DummyApplication()
    bot.check_lock = asyncio.Lock()
    await bot.check_month_command(update, context)
    assert "Using cached result" not in (update.message.last_text or "")
    assert "month navigation" in update.message.last_text


@pytest.mark.asyncio
async def test_check_rejects_month_cache():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot._update_cache_after_scrape(bot.cache, TOKYO_RESULT, use_month_navigation=True)
    bot.application = DummyApplication()
    bot.check_lock = asyncio.Lock()
    await bot.check_command(update, context)
    assert "Using cached result" not in (update.message.last_text or "")
    assert "Checking for available slots" in update.message.last_text

@pytest.mark.asyncio
async def test_check_month_command_cache_expired():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot.cache['result'] = None
    bot.cache['timestamp'] = None
    bot.application = DummyApplication()
    bot.check_lock = asyncio.Lock()
    await bot.check_month_command(update, context)
    assert "Checking for available slots using month navigation" in update.message.last_text

@pytest.mark.asyncio
async def test_check_month_command_force():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    context.args = ["force"]
    import time
    bot.cache['result'] = TOKYO_RESULT
    bot.cache['timestamp'] = time.time()
    bot.application = DummyApplication()
    bot.check_lock = asyncio.Lock()
    await bot.check_month_command(update, context)
    assert "Checking for available slots using month navigation" in update.message.last_text

@pytest.mark.asyncio
async def test_start_command():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    await bot.start_command(update, context)
    assert "Welcome to Samezu Bot" in update.message.last_text

@pytest.mark.asyncio
async def test_help_command():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    await bot.help_command(update, context)
    assert "Samezu Bot Help" in update.message.last_text

@pytest.mark.asyncio
async def test_status_command():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    await bot.status_command(update, context)
    assert "Status" in update.message.last_text

@pytest.mark.asyncio
async def test_cache_command():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot.cache['timestamp'] = None
    await bot.cache_command(update, context)
    assert "Cache Information" in update.message.last_text

@pytest.mark.asyncio
async def test_link_command():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    await bot.link_command(update, context)
    assert "Reservation Websites" in update.message.last_text
    assert "Tokyo" in update.message.last_text
    assert "Kanagawa" in update.message.last_text
    assert "Saitama" in update.message.last_text

@pytest.mark.asyncio
async def test_unsubscribe_command():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    # Patch get_subscribers to simulate user is subscribed
    bot.get_subscribers = lambda: [(str(update.effective_chat.id), "@testuser")]
    bot.remove_subscriber = lambda chat_id: None
    await bot.unsubscribe_command(update, context)
    assert "You have been unsubscribed" in update.message.last_text

@pytest.mark.asyncio
async def test_unsubscribe_command_not_subscribed():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    # Patch get_subscribers to simulate user is NOT subscribed
    bot.get_subscribers = lambda: []
    await bot.unsubscribe_command(update, context)
    assert "You are not currently subscribed" in update.message.last_text


# --- _background_check_task source-aware filtering ---


async def _run_background_check(bot, source, fake_result):
    """Helper: run _background_check_task with a mocked checker result."""
    messages_sent = []

    async def capture_send(chat_id, text, parse_mode='HTML'):
        messages_sent.append(text)

    bot._telegram_send = capture_send

    async def fake_run_check(*args, **kwargs):
        return fake_result

    scrape_key = bot._scrape_key_for_check(source)
    checker, _cache = bot._checker_and_cache_for_scrape_key(scrape_key)
    checker.run_check = fake_run_check

    bot.waiting_users[scrape_key].add((DummyUser.id, DummyChat.id, source, True, False, False))

    await bot._background_check_task(None, source=source, scrape_key=scrape_key)
    return messages_sent


@pytest.mark.asyncio
async def test_check_kanagawa_cache_hit_uses_kanagawa_filter():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    context.args = ["kanagawa"]
    import time
    bot.kanagawa_cache['result'] = KANAGAWA_RESULT
    bot.kanagawa_cache['timestamp'] = time.time()
    await bot.check_command(update, context)
    assert "Using cached result" in update.message.last_text
    assert '普通車ＡＭ' in update.message.last_text
    assert '住民票のある方' not in update.message.last_text
    assert '❌' not in update.message.last_text


@pytest.mark.asyncio
async def test_background_check_kanagawa_shows_kanagawa_slots():
    bot = SamezuBot()
    messages = await _run_background_check(bot, source="kanagawa", fake_result=KANAGAWA_RESULT)
    assert len(messages) == 1
    assert '普通車ＡＭ' in messages[0]
    assert '普通車ＰＭ' in messages[0]


@pytest.mark.asyncio
async def test_background_check_kanagawa_does_not_apply_tokyo_filter():
    bot = SamezuBot()
    messages = await _run_background_check(bot, source="kanagawa", fake_result=KANAGAWA_RESULT)
    assert len(messages) == 1
    assert '住民票のある方' not in messages[0]
    assert '❌' not in messages[0]


@pytest.mark.asyncio
async def test_background_check_tokyo_shows_tokyo_slots():
    bot = SamezuBot()
    messages = await _run_background_check(bot, source=None, fake_result=TOKYO_RESULT)
    assert len(messages) == 1
    assert '住民票のある方' in messages[0]


@pytest.mark.asyncio
async def test_background_check_tokyo_does_not_show_kanagawa_types():
    bot = SamezuBot()
    messages = await _run_background_check(bot, source=None, fake_result=TOKYO_RESULT)
    assert '普通車ＡＭ' not in messages[0]


@pytest.mark.asyncio
async def test_check_saitama_cache_hit_uses_saitama_filter():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    context.args = ["saitama"]
    import time
    bot.saitama_cache['result'] = SAITAMA_RESULT
    bot.saitama_cache['timestamp'] = time.time()
    await bot.check_command(update, context)
    assert "Using cached result" in update.message.last_text
    assert '【１】１回目（初めて）' in update.message.last_text
    assert '住民票のある方' not in update.message.last_text
    assert '❌' not in update.message.last_text


@pytest.mark.asyncio
async def test_background_check_saitama_shows_saitama_slots():
    bot = SamezuBot()
    messages = await _run_background_check(bot, source="saitama", fake_result=SAITAMA_RESULT)
    assert len(messages) == 1
    assert '【１】１回目（初めて）' in messages[0]


@pytest.mark.asyncio
async def test_background_check_saitama_does_not_apply_tokyo_filter():
    bot = SamezuBot()
    messages = await _run_background_check(bot, source="saitama", fake_result=SAITAMA_RESULT)
    assert len(messages) == 1
    assert '住民票のある方' not in messages[0]
    assert '❌' not in messages[0]
