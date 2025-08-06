import pytest
from samezu_bot.run_bot import SamezuBot

def test_add_subscriber():
    bot = SamezuBot()
    bot.add_subscriber("12345")
    assert "12345" in [s[0] for s in bot.get_subscribers()]
