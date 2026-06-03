"""Logging setup must expose bot.log when run_bot is imported."""

import logging


def test_import_run_bot_configures_bot_log_handler():
    import run_bot  # noqa: F401

    root = logging.getLogger()
    log_files = [
        getattr(h, 'baseFilename', '')
        for h in root.handlers
        if isinstance(h, logging.FileHandler)
    ]
    assert any(path.endswith('bot.log') for path in log_files)
    assert any(path.endswith('reservation_checker.log') for path in log_files)
