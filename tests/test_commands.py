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
    bot.cache['result'] = "Test result"
    bot.cache['timestamp'] = asyncio.get_event_loop().time()
    bot.is_cache_valid = lambda: True
    bot.get_cache_age = lambda: 30
    await bot.check_command(update, context)
    assert "Using cached result" in update.message.last_text

@pytest.mark.asyncio
async def test_check_command_cache_expired():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot.cache['result'] = None
    bot.cache['timestamp'] = None
    bot.is_cache_valid = lambda: False
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
    bot.cache['result'] = "Test result"
    bot.cache['timestamp'] = asyncio.get_event_loop().time()
    bot.is_cache_valid = lambda: True
    bot.application = DummyApplication()
    bot.check_lock = asyncio.Lock()
    await bot.check_command(update, context)
    assert "Checking for available slots" in update.message.last_text

@pytest.mark.asyncio
async def test_check_month_command_cache_valid():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot.cache['result'] = "Test result"
    bot.cache['timestamp'] = asyncio.get_event_loop().time()
    bot.is_cache_valid = lambda: True
    bot.get_cache_age = lambda: 30
    await bot.check_month_command(update, context)
    assert "Using cached result" in update.message.last_text

@pytest.mark.asyncio
async def test_check_month_command_cache_expired():
    bot = SamezuBot()
    update = DummyUpdate()
    context = DummyContext()
    bot.cache['result'] = None
    bot.cache['timestamp'] = None
    bot.is_cache_valid = lambda: False
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
    bot.cache['result'] = "Test result"
    bot.cache['timestamp'] = asyncio.get_event_loop().time()
    bot.is_cache_valid = lambda: True
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
    assert "Reservation System Website" in update.message.last_text

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
