# Samezu Bot

Telegram bot that monitors **Tokyo** (府中・鮫洲) and **Kanagawa** (外国免許四輪車) driving-test reservation calendars and notifies subscribers when slots open.

**Production entrypoint:** `python run_bot.py` (systemd on VPS). See [docs/CONTRACT.md](docs/CONTRACT.md) for source routing, cache, and notification rules.

## Features

- Automated checks every 5 minutes (Tokyo + Kanagawa)
- Per-subscriber sources (`samezu`, `fuchu`, `kanagawa`) and slot-type filters (`ari`, `nai`, `am`, `pm`, `all`)
- Manual `/check` and `/check_month` with shared scrape lock and per-source wait queues
- Result cache with duplicate-notification suppression
- Playwright scraper (headless Chromium) with Cloudflare waiting-room handling

## Requirements

- Python 3.8+
- Chromium (via Playwright)
- Telegram bot token ([BotFather](https://t.me/BotFather))

## Quick start

```bash
git clone <your-repo-url>
cd samezu_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp config_template.py config.py
# Edit config.py — set TELEGRAM_BOT_TOKEN (or use env on the server)

python run_bot.py
```

**Important:** Do not run `python run_bot.py` locally while the same bot token is active on the VPS — Telegram updates will conflict. Use a separate test token locally, or stop the remote service first.

## Telegram commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome and status |
| `/help` | Full command list |
| `/check` | Check slots (2-week navigation; Tokyo default) |
| `/check_month` | Same as `/check` with 1-month navigation |
| `/check kanagawa` | Kanagawa calendar |
| `/check samezu` / `/check fuchu` | Tokyo, single facility |
| `/check force` | Fresh scrape (ignore cache) |
| `/check all` | All slot types for selected source |
| `/subscribe` | Subscribe (see options below) |
| `/unsubscribe` | Remove subscription |
| `/status` | Bot and cache status |
| `/cache` | Detailed cache info |
| `/link` | Reservation URLs |

### Subscribe examples

Stored in `subscribers.txt` as `chat_id|username|sources|type`.

```text
/subscribe                          # Tokyo (samezu+fuchu), relevant slots
/subscribe kanagawa                   # Kanagawa only
/subscribe samezu fuchu               # Tokyo facilities only
/subscribe kanagawa am                # 普通車ＡＭ only
/subscribe nai | ari | pm | all       # Slot-type filters
```

Tokyo “relevant” default: 住民票のある方. Kanagawa relevant: 普通車ＡＭ and 普通車ＰＭ.

## Sources (subscriber vs scheduler)

| You subscribe / `/check` | Scheduler scrapes | Facility filter |
|--------------------------|-------------------|-----------------|
| `samezu` | `tokyo` | 鮫洲試験場 |
| `fuchu` | `tokyo` | 府中試験場 |
| `samezu` + `fuchu` | `tokyo` | both |
| `kanagawa` | `kanagawa` | 外国免許四輪車 |

Details: [docs/CONTRACT.md](docs/CONTRACT.md).

## Configuration

Defaults live in `config_template.py`; override in `config.py` (gitignored) or via environment on the VPS.

| Variable | Default | Purpose |
|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | — | Bot token |
| `CHECK_INTERVAL` | 300 | Seconds between scheduled checks |
| `CACHE_DURATION` | 120 | Cache TTL (seconds) |
| `TARGET_FACILITIES` / `TARGET_SLOT_TYPES` | Tokyo | 府中・鮫洲, 住民票のある方 |
| `KANAGAWA_*` | — | Kanagawa URL, facility, AM/PM types |
| `HEADLESS` | `True` | Playwright headless mode |
| `TIMEOUT` | 30000 | Page load timeout (ms) |

## Logs

`app_logging.configure_logging()` runs before the scraper loads.

| Output | Contents |
|--------|----------|
| `bot.log` | `run_bot` logger — commands, scheduler, cache, notifications |
| `reservation_checker.log` | Playwright / HTTP scraper loggers |
| stderr / `journalctl` | All loggers (systemd captures stderr) |

On VPS: `sudo journalctl -u samezu_bot -f` and `tail -f bot.log reservation_checker.log`.

Missed alerts: [docs/OPERATIONAL_RISKS.md](docs/OPERATIONAL_RISKS.md).

## Testing

```bash
source venv/bin/activate
pytest -q    # tests/ only (pytest.ini); 100+ hermetic tests, no live network
```

Manual probes belong in `scripts/` or local-only files (see `.gitignore`). Calendar HTML samples live under `tests/fixtures/` (refresh with `scripts/capture_calendar_fixture.py`).

## Deployment (VPS)

Production uses systemd (`deploy/samezu_bot.service`):

```ini
ExecStart=/home/ubuntu/samezu_bot/venv/bin/python run_bot.py
```

From your machine (after pushing to `main`):

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

This SSHs to the server, `git pull`, runs `pytest`, and restarts `samezu_bot`. See [CLAUDE.md](CLAUDE.md) for host, SSH key, and manual commands.

## Project layout

```text
samezu_bot/
├── run_bot.py                         # Production Telegram bot
├── reservation_checker_playwright.py  # Playwright scraper
├── app_logging.py                     # bot.log / scraper log split
├── config_template.py                 # Defaults
├── config.py                          # Local overrides (gitignored)
├── docs/
│   ├── CONTRACT.md                    # Runtime behavior spec
│   └── OPERATIONAL_RISKS.md           # CI vs live site, debugging
├── scripts/
│   ├── deploy.sh                      # VPS deploy
│   ├── README.md
│   └── reservation_checker_requests.py  # HTTP experiment (not production)
├── deploy/samezu_bot.service          # systemd unit template
├── tests/
│   ├── fixtures/                      # Saved calendar HTML (parser tests)
│   └── ...                            # pytest suite
└── pytest.ini
```

## Scraping and debugging

| Script | Use |
|--------|-----|
| `python run_bot.py` | **Production** — filtered notifications |
| `python reservation_checker_playwright.py` | Debug scrape; prints only, no Telegram |
| `python scripts/reservation_checker_requests.py` | HTTP experiment; prints only |

Standalone scrapers do **not** apply subscriber/source filters. Telegram from a scraper requires `ALLOW_STANDALONE_NOTIFY=1` and is for debugging only — use `run_bot.py` in production.

## Security

- `config.py`, `subscribers.txt`, and `*.log` are gitignored
- Do not commit tokens or subscriber chat IDs
- Use a dedicated VPS SSH key and restrict `TELEGRAM_BOT_TOKEN` to the service environment

## Built with

Python · Playwright · [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) · asyncio

## License

Personal use only.
