import pytest
import asyncio
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
    # Patch add_subscriber to track calls
    called = {}
    def fake_add_subscriber(chat_id, user_info=None):
        called['chat_id'] = chat_id
    bot.add_subscriber = fake_add_subscriber
    await bot.subscribe_command(DummyUpdate(), DummyContext())
    assert called['chat_id'] == 12345
