"""One-time logging setup for the bot process (call before importing the scraper)."""

import logging

_CONFIGURED = False


def configure_logging() -> None:
    """Attach stdout and bot/scraper log files to the root logger (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        root.addHandler(stream_handler)

    for log_path in ('bot.log', 'reservation_checker.log'):
        already = any(
            isinstance(h, logging.FileHandler)
            and log_path in getattr(h, 'baseFilename', '')
            for h in root.handlers
        )
        if not already:
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)

    _CONFIGURED = True
