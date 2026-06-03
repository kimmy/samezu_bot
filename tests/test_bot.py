import pytest
from run_bot import SamezuBot


def test_add_subscriber(tmp_path, monkeypatch):
    bot = SamezuBot()
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(tmp_path / 'subscribers.txt'))
    bot.add_subscriber("12345")
    assert "12345" in [s[0] for s in bot.get_subscribers()]
