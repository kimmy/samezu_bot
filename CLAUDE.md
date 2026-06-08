# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Configure credentials
cp config_template.py config.py
# Edit config.py and set TELEGRAM_BOT_TOKEN

# Run the bot
python run_bot.py

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_async.py

# Run a single test
pytest tests/test_async.py::test_subscribe_command
```

## Deployment

Hosted on a VPS via systemd. Prefer the deploy script (runs `pytest` on the server before restart):

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Manual equivalent:

```bash
ssh -i ~/.ssh/samezu_bot2.key ubuntu@131.186.56.62 \
  "cd ~/samezu_bot && git pull && ./venv/bin/python -m pytest -q && sudo systemctl restart samezu_bot && sudo systemctl status samezu_bot --no-pager"

# Check logs on the server
ssh -i ~/.ssh/samezu_bot2.key ubuntu@131.186.56.62 "sudo journalctl -u samezu_bot -f"
```

**Do not run `python run_bot.py` locally while the VPS is active** — both instances will compete for the same Telegram updates and users will get split/missing responses. Stop the service first or use a separate test bot token in `config.py`.

**Do not use `python reservation_checker_playwright.py` for production notifications** — it bypasses subscriber/source filtering. Use `run_bot.py` only. See `docs/CONTRACT.md` and `docs/OPERATIONAL_RISKS.md`.

## Architecture

The bot has two main modules and a config layer:

**`run_bot.py`** — The Telegram bot layer. `SamezuBot` handles command handlers, per-source caches of `CheckResult`, subscriber management, and the background scheduler. Filtering and Telegram HTML use `domain.format_check_message()` at read/notify time (not HTML string parsing).

**`domain.py`** — `Slot` and `CheckResult` types; `filter_slots()`, `render_slots_message()`, `format_check_message()`.

**`reservation_checker_playwright.py`** — Playwright scraper. Returns `CheckResult` from `run_check()`; detects slots via `aria-label="予約可能"`. Handles Kanagawa calendar `rowspan` on facility cells. Two instances (Tokyo + Kanagawa).

**Config layer** — Both modules do `from config_template import *` then attempt `import config` to override. `config_template.py` provides safe defaults; `config.py` (gitignored) holds local overrides. On the VPS, a `.env` or the systemd unit supplies `TELEGRAM_BOT_TOKEN`.

**Multi-source design** — Two `ReservationChecker` instances run in `SamezuBot`:
- `self.reservation_checker` — Tokyo (府中試験場, 鮫洲試験場), slot type filter: `住民票のある方`
- `self.kanagawa_checker` — Kanagawa (外国免許四輪車), slot type filter: `普通車ＡＭ`, `普通車ＰＭ`

Each has its own cache dict (`self.cache` / `self.kanagawa_cache`). The scheduler runs both and notifies subscribers per their selected sources.

**Subscriber storage** — `subscribers.txt` stores one subscriber per line as `chat_id|username|sources|type` (pipe-delimited).
- `sources`: comma-separated list — `samezu`, `fuchu`, `kanagawa` (old 2-field entries default to all sources)
- `type`: `relevant` (default), `all`, `nai` (住民票のない方 only), `ari` (住民票のある方 only), `am` (普通車ＡＭ only, Kanagawa), `pm` (普通車ＰＭ only, Kanagawa)

**Caching** — One `CheckResult` per scrape key (`cache` / `kanagawa_cache`). Subscriber and `/check` filters applied when rendering messages. Duration: `CACHE_DURATION` seconds (default 120s).

**Scheduler notifications** — After each check, `scheduler_notify_signature()` (relevant slot types) is compared against `self.last_notified[source]`. Notifications are only sent if the slot set changed. When no relevant slots are found, `last_notified` resets so a future reappearance triggers a fresh notification.

**Tests** — Default `pytest` includes Playwright-on-fixture tests (`tests/test_playwright_fixtures.py`). Live-site smoke: `LIVE_SCRAPE=1 pytest -m live`.

**Concurrency** — `check_lock` (an `asyncio.Lock`) prevents concurrent scrapes. `waiting_users` is keyed by scrape key (`tokyo` / `kanagawa`); incompatible waiters are re-queued and chained scrapes run via `_start_chained_scrapes_for_remaining_waiters()`. Scheduler source `tokyo` matches subscriber sources `samezu` / `fuchu`.

## Key Configuration Values (config_template.py)

| Variable | Default | Purpose |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | env var | Bot token from BotFather |
| `TARGET_FACILITIES` | 府中試験場, 鮫洲試験場 | Tokyo facilities to monitor |
| `TARGET_SLOT_TYPES` | 住民票のある方 | Tokyo level-2 row filter |
| `KANAGAWA_TARGET_URL` | e-kanagawa URL | Kanagawa reservation page |
| `KANAGAWA_TARGET_FACILITIES` | 外国免許四輪車 | Kanagawa level-1 row filter |
| `KANAGAWA_TARGET_SLOT_TYPES` | 普通車ＡＭ, 普通車ＰＭ | Kanagawa level-2 row filter |
| `CHECK_INTERVAL` | 300s | Scheduler frequency |
| `CACHE_DURATION` | 120s | How long cached results are valid |
| `HEADLESS` | True | Set False for browser debugging |
| `TIMEOUT` | 30000ms | Playwright page load timeout |

## Logs

Configured by `app_logging.configure_logging()` before the scraper import:

- **Console (stderr)** — all loggers via root propagation
- **`bot.log`** — logger `run_bot` (used by `run_bot.py`; production entry is `python run_bot.py`)
- **`reservation_checker.log`** — loggers `reservation_checker_playwright` and `reservation_checker_requests`

When a scraper file is run as `python script.py`, logger `__main__` is also routed to the matching log file via `sys.argv[0]`.
