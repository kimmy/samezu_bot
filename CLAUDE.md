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

Hosted on a VPS via systemd. To deploy:

```bash
# SSH into the server and pull + restart
ssh -i ~/.ssh/samezu_bot2.key ubuntu@131.186.56.62 \
  "cd ~/samezu_bot && git pull && sudo systemctl restart samezu_bot && sudo systemctl status samezu_bot --no-pager"

# Check logs on the server
ssh -i ~/.ssh/samezu_bot2.key ubuntu@131.186.56.62 "sudo journalctl -u samezu_bot -f"
```

**Do not run `python run_bot.py` locally while the VPS is active** — both instances will compete for the same Telegram updates and users will get split/missing responses. Stop the service first or use a separate test bot token in `config.py`.

## Architecture

The bot has two main modules and a config layer:

**`run_bot.py`** — The Telegram bot layer. `SamezuBot` handles all command handlers (`/check`, `/subscribe`, etc.), in-memory caching of scrape results per source, subscriber management (read/write `subscribers.txt`), filtering logic (by slot type), and a background scheduler (`asyncio` task that runs every `CHECK_INTERVAL` seconds). `BotRunner` wires up signal handling and the `python-telegram-bot` polling loop.

**`reservation_checker_playwright.py`** — The web scraping layer. `ReservationChecker` accepts `target_url`, `target_facilities`, `target_slot_types`, and `source_name` as constructor params. It uses Playwright (headless Chromium) to navigate the reservation website, clicking navigation buttons (`2週後＞` or `1か月後＞`) and detecting available slots via SVG elements with `aria-label="予約可能"`. Results are a list of `{date, facility, applicant_type}` dicts. One class, two instances (Tokyo + Kanagawa).

**Config layer** — Both modules do `from config_template import *` then attempt `import config` to override. `config_template.py` provides safe defaults; `config.py` (gitignored) holds local overrides. On the VPS, a `.env` or the systemd unit supplies `TELEGRAM_BOT_TOKEN`.

**Multi-source design** — Two `ReservationChecker` instances run in `SamezuBot`:
- `self.reservation_checker` — Tokyo (府中試験場, 鮫洲試験場), slot type filter: `住民票のある方`
- `self.kanagawa_checker` — Kanagawa (外国免許四輪車), slot type filter: `普通車ＡＭ`, `普通車ＰＭ`

Each has its own cache dict (`self.cache` / `self.kanagawa_cache`). The scheduler runs both and notifies subscribers per their selected sources.

**Subscriber storage** — `subscribers.txt` stores one subscriber per line as `chat_id|username|sources|type` (pipe-delimited).
- `sources`: comma-separated list — `samezu`, `fuchu`, `kanagawa` (old 2-field entries default to all sources)
- `type`: `relevant` (default), `all`, `nai` (住民票のない方 only), `ari` (住民票のある方 only)

**Caching** — One unfiltered cache per source. Filtering applied at read time. Duration: `CACHE_DURATION` seconds (default 120s).

**Concurrency** — `check_lock` (an `asyncio.Lock`) prevents concurrent scrapes. Users who request a check while one is in progress are added to `waiting_users` and receive the result when the running check completes.

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

- `bot.log` — Telegram bot events
- `reservation_checker.log` — Scraper events (page navigation, slot detection)
