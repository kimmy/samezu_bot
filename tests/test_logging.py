"""Logging setup: split files, script entrypoints, console on root."""

import logging
import subprocess
import sys
from pathlib import Path

import app_logging

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE = Path(__file__).resolve().parent / 'log_entry_probe.py'


def _reset_logging():
    app_logging._CONFIGURED = False
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    for name in (
        app_logging.BOT_LOGGER_NAME,
        '__main__',
        *app_logging.SCRAPER_LOGGER_NAMES,
    ):
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            logger.removeHandler(handler)


def _run_probe(tmp_path: Path, mode: str, script_name: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(PROBE),
            str(tmp_path),
            str(REPO_ROOT),
            mode,
            script_name,
        ],
        check=True,
        cwd=REPO_ROOT,
    )


def test_configure_logging_splits_bot_and_scraper_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _reset_logging()
    app_logging.configure_logging()

    root = logging.getLogger()
    assert any(app_logging._is_console_handler(h) for h in root.handlers)
    assert not any(isinstance(h, logging.FileHandler) for h in root.handlers)

    bot_logger = logging.getLogger(app_logging.BOT_LOGGER_NAME)
    assert any(
        isinstance(h, logging.FileHandler) for h in bot_logger.handlers
    )

    scraper_logger = logging.getLogger(app_logging.SCRAPER_LOGGER_NAME)
    assert any(
        isinstance(h, logging.FileHandler) for h in scraper_logger.handlers
    )


def test_script_entrypoint_run_bot_named_logger_writes_bot_log(tmp_path):
    _run_probe(tmp_path, 'bot_named', 'run_bot.py')
    assert 'PROBE_BOT_NAMED' in (tmp_path / 'bot.log').read_text(encoding='utf-8')
    assert 'PROBE_BOT_NAMED' not in (tmp_path / 'reservation_checker.log').read_text(
        encoding='utf-8'
    )


def test_script_entrypoint_run_bot_main_logger_writes_bot_log(tmp_path):
    """python run_bot.py uses logger name __main__ unless module uses BOT_LOGGER_NAME."""
    _run_probe(tmp_path, 'bot_main', 'run_bot.py')
    assert 'PROBE_BOT_MAIN' in (tmp_path / 'bot.log').read_text(encoding='utf-8')


def test_script_entrypoint_playwright_named_logger_writes_scraper_log(tmp_path):
    _run_probe(tmp_path, 'scraper_named', 'reservation_checker_playwright.py')
    text = (tmp_path / 'reservation_checker.log').read_text(encoding='utf-8')
    assert 'PROBE_SCRAPER_NAMED' in text
    assert 'PROBE_SCRAPER_NAMED' not in (tmp_path / 'bot.log').read_text(encoding='utf-8')


def test_script_entrypoint_playwright_main_logger_writes_scraper_log(tmp_path):
    _run_probe(tmp_path, 'scraper_main', 'reservation_checker_playwright.py')
    assert 'PROBE_SCRAPER_MAIN' in (
        tmp_path / 'reservation_checker.log'
    ).read_text(encoding='utf-8')


def test_import_run_bot_uses_bot_logger_name(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    _reset_logging()
    import importlib
    import run_bot

    importlib.reload(run_bot)
    assert run_bot.logger.name == app_logging.BOT_LOGGER_NAME
    run_bot.logger.info('PROBE_IMPORT')
    assert 'PROBE_IMPORT' in (tmp_path / 'bot.log').read_text(encoding='utf-8')


def test_console_handler_detection_excludes_file_handler():
    file_handler = logging.FileHandler('test.log')
    assert not app_logging._is_console_handler(file_handler)
    console = logging.StreamHandler(sys.stderr)
    assert app_logging._is_console_handler(console)
