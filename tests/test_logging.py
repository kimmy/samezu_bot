"""Logging setup: split files, console on root, no FileHandler-as-StreamHandler bug."""

import logging
import sys

import app_logging


def _reload_logging_modules():
    """Re-import run_bot after resetting configure flag (test isolation)."""
    import importlib
    import run_bot

    importlib.reload(run_bot)
    return run_bot


def test_configure_logging_splits_bot_and_scraper_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app_logging._CONFIGURED = False
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for name in (app_logging.BOT_LOGGER_NAME, *app_logging.SCRAPER_LOGGER_NAMES):
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

    app_logging.configure_logging()

    root = logging.getLogger()
    assert any(app_logging._is_console_handler(h) for h in root.handlers)
    assert not any(isinstance(h, logging.FileHandler) for h in root.handlers)

    bot_logger = logging.getLogger(app_logging.BOT_LOGGER_NAME)
    bot_files = [
        getattr(h, 'baseFilename', '')
        for h in bot_logger.handlers
        if isinstance(h, logging.FileHandler)
    ]
    assert any(str(tmp_path / 'bot.log') in p or p.endswith('bot.log') for p in bot_files)

    scraper_logger = logging.getLogger('reservation_checker_playwright')
    scraper_files = [
        getattr(h, 'baseFilename', '')
        for h in scraper_logger.handlers
        if isinstance(h, logging.FileHandler)
    ]
    assert any(
        str(tmp_path / 'reservation_checker.log') in p or p.endswith('reservation_checker.log')
        for p in scraper_files
    )


def test_import_run_bot_configures_named_loggers(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    app_logging._CONFIGURED = False
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)

    _reload_logging_modules()

    bot_logger = logging.getLogger('run_bot')
    assert any(isinstance(h, logging.FileHandler) for h in bot_logger.handlers)

    scraper_logger = logging.getLogger('reservation_checker_playwright')
    assert any(isinstance(h, logging.FileHandler) for h in scraper_logger.handlers)


def test_console_handler_detection_excludes_file_handler():
    file_handler = logging.FileHandler('test.log')
    assert not app_logging._is_console_handler(file_handler)
    console = logging.StreamHandler(sys.stderr)
    assert app_logging._is_console_handler(console)
