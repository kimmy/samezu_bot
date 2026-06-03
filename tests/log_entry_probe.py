"""Helper for tests: emulate script entrypoint logging (not collected by pytest)."""

import logging
import sys
from pathlib import Path


def main() -> None:
    cwd = Path(sys.argv[1]).resolve()
    repo_root = Path(sys.argv[2]).resolve()
    mode = sys.argv[3]
    script_name = sys.argv[4]

    sys.path.insert(0, str(repo_root))
    import os

    os.chdir(cwd)
    sys.argv = [script_name]

    from app_logging import BOT_LOGGER_NAME, SCRAPER_LOGGER_NAME, configure_logging

    configure_logging()

    if mode == 'bot_named':
        log = logging.getLogger(BOT_LOGGER_NAME)
        log.info('PROBE_BOT_NAMED')
    elif mode == 'bot_main':
        log = logging.getLogger('__main__')
        log.info('PROBE_BOT_MAIN')
    elif mode == 'scraper_named':
        log = logging.getLogger(SCRAPER_LOGGER_NAME)
        log.info('PROBE_SCRAPER_NAMED')
    elif mode == 'scraper_main':
        log = logging.getLogger('__main__')
        log.info('PROBE_SCRAPER_MAIN')
    else:
        raise SystemExit(f'unknown mode: {mode}')


if __name__ == '__main__':
    main()
