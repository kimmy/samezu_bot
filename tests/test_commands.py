class DummyApplication:
    def create_task(self, coro):
        return None
import pytest
import asyncio
from run_bot import SamezuBot

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
async def test_check_command_cache_valid():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    import time
    bot.cache['result'] = "Test result"
    bot.cache['timestamp'] = time.time()
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
    bot.cache['result'] = "Test result"
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
    import time
    bot.cache['result'] = "Test result"
    bot.cache['timestamp'] = time.time()
    await bot.check_month_command(update, context)
    assert "Using cached result" in update.message.last_text

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
    bot.cache['result'] = "Test result"
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

KANAGAWA_RESULT = (
    "🎉 <b>Available Reservation Slots Found!</b>\n\n"
    "📍 <b>Facilities:</b> 外国免許四輪車\n\n"
    "<b>To book, click the <i>予約可能 (reservable)</i> or <i>選択中 (selected)</i> mark on your desired date on the calendar. Then proceed with the booking process.</b>\n\n"
    "📅 <b>06/05 (Thu)</b>\n"
    "   🏢 <b>外国免許四輪車</b>\n"
    "      • 普通車ＡＭ — <a href='http://example.com'>Book</a>\n"
    "      • 普通車ＰＭ — <a href='http://example.com'>Book</a>\n"
    "\n"
    "🔗 <a href='http://example.com'>Book Now</a>"
)

TOKYO_RESULT = (
    "🎉 <b>Available Reservation Slots Found!</b>\n\n"
    "📍 <b>Facilities:</b> 鮫洲試験場\n\n"
    "<b>To book, click the <i>予約可能 (reservable)</i> or <i>選択中 (selected)</i> mark on your desired date on the calendar. Then proceed with the booking process.</b>\n\n"
    "📅 <b>06/05 (Thu)</b>\n"
    "   🏢 <b>鮫洲試験場</b>\n"
    "      • 住民票のある方 — <a href='http://example.com'>Book</a>\n"
    "\n"
    "🔗 <a href='http://example.com'>Book Now</a>"
)


async def _run_background_check(bot, source, fake_result):
    """Helper: run _background_check_task with a mocked checker result."""
    messages_sent = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            messages_sent.append(text)

    class FakeContext:
        bot = FakeBot()

    async def fake_run_check(*args, **kwargs):
        return fake_result

    if source == "kanagawa":
        bot.kanagawa_checker.run_check = fake_run_check
    else:
        bot.reservation_checker.run_check = fake_run_check

    bot.waiting_users.add((DummyUser.id, DummyChat.id))

    context = FakeContext()
    await bot._background_check_task(context, source=source)
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
