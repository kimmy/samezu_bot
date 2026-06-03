# Samezu Bot

A Python-based Telegram bot that monitors Tokyo (府中・鮫洲) and Kanagawa driving-test reservation calendars and sends Telegram notifications when slots open.

## Features

- 🔍 **Automated Checking**: Monitors 府中試験場, 鮫洲試験場 (Tokyo), and 外国免許四輪車 (Kanagawa)
- 📱 **Telegram Notifications**: Sends instant notifications when slots are found
- ⚙️ **Flexible Configuration**: Support for multiple users with customizable notification preferences
- 🔒 **Secure**: Local configuration with sensitive data kept private
- 🚀 **Easy Setup**: Simple installation and configuration process
- ⏰ **Scheduled Checking**: Automatically checks every 5 minutes
- 📅 **Multiple Navigation**: Supports both 2-week and 1-month navigation
- 🏷️ **User Tagging**: Tags users in notifications for easy identification

## Requirements

- Python 3.8+
- Chrome/Chromium browser
- Telegram Bot Token
- Chat IDs for notifications

## Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd samezu_bot
   ```

2. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Configuration

### Local Setup

1. **Copy the config template:**
   ```bash
   cp config_template.py config.py
   ```

2. **Update config.py with your credentials:**
   ```python
   # Telegram Bot Configuration
   TELEGRAM_BOT_TOKEN = "your_actual_bot_token_here"
   
   # Other settings are already configured in config_template.py
   ```

3. **Get your Telegram Bot Token:**
   - Message @BotFather on Telegram
   - Create a new bot: `/newbot`
   - Copy the token provided

4. **Get your Chat ID:**
   - Message your bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Look for your `chat_id` in the response

## Usage

### Start the Bot

```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python run_bot.py
```

### Bot Commands

Once the bot is running, you can use these commands in Telegram:

- `/start` - Welcome message and bot status
- `/check` - Check slots (2-week navigation; Tokyo by default)
- `/check kanagawa` - Kanagawa calendar
- `/check samezu` or `/check fuchu` - Tokyo, one facility
- `/check_month` - Same as `/check` but 1-month navigation
- `/check force` - Force a fresh scrape (ignore cache)
- `/check all` - Show all slot types for the selected source
- `/status` - Check bot status and last check time
- `/cache` - Show detailed cache information and timestamp
- `/link` - Get the reservation system website
- `/help` - Show available commands

### Subscription Options

Subscribers are stored in `subscribers.txt` as `chat_id|username|sources|type`.

- `/subscribe` — All Tokyo sources, relevant slot types (住民票のある方)
- `/subscribe kanagawa` — Kanagawa only (普通車ＡＭ/ＰＭ)
- `/subscribe samezu fuchu` — Tokyo facilities
- `/subscribe nai` / `ari` / `am` / `pm` — Slot-type filters
- `/subscribe all` — All sources, all slot types
- `/unsubscribe` — Remove subscription

### Automatic Checking

The bot automatically checks for slots every 5 minutes. You'll receive notifications when:
- ✅ Slots become available (based on your subscription type)
- ⚠️ Errors occur during checking

## Configuration Options

### Check Interval

Modify `CHECK_INTERVAL` in `config.py` to change how often the bot checks for slots (default: 300 seconds = 5 minutes).

### Cache Duration

Modify `CACHE_DURATION` in `config.py` to change how long results are cached (default: 120 seconds = 2 minutes).

### Target Facilities

The bot checks these facilities by default:
- 府中試験場 (Fuchu Test Center)
- 鮫洲試験場 (Samezu Test Center)

You can modify `TARGET_FACILITIES` in `config.py` to add or remove facilities.

### Filtering Configuration

- `SHOW_ONLY_RELEVANT_APPLICANTS`: Set to `True` to show only slots for "住民票のある方" (default: True)
- Set to `False` to show all available slots

### Timeout Configuration

- `TIMEOUT`: Main timeout for page operations (default: 30000ms = 30 seconds)
- `LOADING_INDICATOR_TIMEOUT`: Timeout for loading indicators (default: 5000ms = 5 seconds)
- `PAGE_TRANSITION_WAIT`: Wait time after page transitions (default: 3000ms = 3 seconds)
- `DYNAMIC_CONTENT_WAIT`: Wait time for dynamic content (default: 2000ms = 2 seconds)

## Running Locally

### Keep Your Laptop Awake

Since you're running locally, make sure your laptop stays awake:

- **macOS**: System Preferences > Energy Saver > Prevent computer from sleeping
- **Windows**: Power & Sleep settings > Never sleep
- **Linux**: Disable sleep mode in power management

### Background Running

The bot will continue running even if you lock your laptop, but it will stop if your laptop goes to sleep.

## Troubleshooting

### Common Issues

1. **"externally-managed-environment" error:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Playwright browser issues:**
   ```bash
   playwright install chromium
   ```

3. **Telegram bot not responding:**
   - Check your bot token in `config.py`
   - Make sure you've messaged your bot first
   - Try the `/start` command

4. **Import errors:**
   - Make sure you're in the virtual environment
   - Check that all dependencies are installed

### Logs

After `python run_bot.py` (production entrypoint):

- **`bot.log`** — bot/scheduler (`run_bot` logger)
- **`reservation_checker.log`** — Playwright scraper only
- **stderr** — same records via journalctl when using systemd

See `docs/OPERATIONAL_RISKS.md` for debugging missed alerts.

## Security

- ✅ Sensitive data stored locally in `config.py`
- ✅ `config.py` excluded from Git (`.gitignore`)
- ✅ No credentials committed to repository
- ✅ Local-only deployment

## Project Structure

```
samezu_bot/
├── run_bot.py                      # Telegram bot, scheduler, cache, notifications
├── reservation_checker_playwright.py  # Playwright scraper (production)
├── config_template.py              # Defaults; override in config.py
├── scripts/deploy.sh               # VPS deploy (pytest + restart)
├── tests/                          # Regression suite (pytest)
├── pytest.ini
└── subscribers.txt                 # Local subscriber store (gitignored)
```

## Built With

- **Python** - Core programming language
- **Playwright** - Web automation and scraping
- **python-telegram-bot** - Telegram bot API integration
- **asyncio** - Asynchronous programming

## Testing

```bash
source venv/bin/activate
pytest -q          # tests/ only (see pytest.ini)
```

## Deployment (VPS)

Production runs on a VPS under systemd. Do not run `python run_bot.py` locally while the VPS bot is active (competing Telegram updates).

```bash
./scripts/deploy.sh   # git pull, pytest on server, systemctl restart
```

See `CLAUDE.md` for SSH host, logs, and architecture notes.

## Development

This project was **vibe coded** using **Cursor** with AI assistance, demonstrating modern development practices and robust error handling.

## License

This project is for personal use only.

---

**Note**: This bot is designed for local use only. For 24/7 operation, consider deploying to a cloud service like Railway, Render, or Fly.io.
