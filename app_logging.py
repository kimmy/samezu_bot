"""One-time logging setup for the bot process (call before importing the scraper)."""

import logging
import sys

_CONFIGURED = False

BOT_LOGGER_NAME = 'run_bot'
SCRAPER_LOGGER_NAMES = (
    'reservation_checker_playwright',
    'reservation_checker_requests',
)


def _is_console_handler(handler: logging.Handler) -> bool:
    """True for stderr/stdout handlers, not on-disk FileHandler subclasses."""
    return isinstance(handler, logging.StreamHandler) and not isinstance(
        handler, logging.FileHandler
    )


def _logger_has_file(logger: logging.Logger, log_path: str) -> bool:
    return any(
        isinstance(h, logging.FileHandler)
        and log_path in getattr(h, 'baseFilename', '')
        for h in logger.handlers
    )


def _attach_file_logger(logger_name: str, log_path: str, formatter: logging.Formatter) -> None:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    if _logger_has_file(logger, log_path):
        return
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def configure_logging() -> None:
    """Console on root; bot.log and reservation_checker.log on named loggers only."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Drop legacy root file handlers (old basicConfig / prior bootstrap).
    for handler in list(root.handlers):
        if isinstance(handler, logging.FileHandler):
            root.removeHandler(handler)

    if not any(_is_console_handler(h) for h in root.handlers):
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        root.addHandler(console)

    _attach_file_logger(BOT_LOGGER_NAME, 'bot.log', formatter)
    for name in SCRAPER_LOGGER_NAMES:
        _attach_file_logger(name, 'reservation_checker.log', formatter)

    _CONFIGURED = True
