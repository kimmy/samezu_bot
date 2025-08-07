# Samezu Bot

A Python-based Telegram bot that automatically checks for available driving test slots at Samezu facilities and sends notifications when slots become available.

## Features

- 🔍 **Automated Checking**: Monitors 府中試験場 and 鮫洲試験場 for available slots
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
- `/check` - Manually check for available slots (2-week navigation)
- `/check_month` - Manually check for available slots (1-month navigation)
- `/check force` or `/check -f` - Force a fresh check, ignoring the cache
- `/check all` or `/check -a` - Show all available slots (not just relevant ones)
- `/status` - Check bot status and last check time
- `/cache` - Show detailed cache information and timestamp
- `/link` - Get the reservation system website
- `/help` - Show available commands

### Subscription Options

The bot supports different subscription types:

- `/subscribe` - Subscribe to relevant slots only (住民票のある方)
- `/subscribe all` - Subscribe to ALL available slots (both types)
- `/subscribe nai` - Subscribe to 住民票のない方 slots only
- `/subscribe ari` - Subscribe to 住民票のある方 slots only
- `/unsubscribe` - Unsubscribe from notifications

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

Check `bot.log` and `reservation_checker.log` for detailed error messages and debugging information.

## Security

- ✅ Sensitive data stored locally in `config.py`
- ✅ `config.py` excluded from Git (`.gitignore`)
- ✅ No credentials committed to repository
- ✅ Local-only deployment

## Project Structure

```
samezu_bot/
├── run_bot.py              # Main bot script
├── reservation_checker.py   # Web scraping logic
├── config_template.py       # Configuration template
├── config.py               # Local configuration (not in Git)
├── requirements.txt         # Python dependencies
├── README.md              # This file
├── .gitignore             # Git ignore rules
├── venv/                  # Virtual environment
├── bot.log                # Bot logs
├── reservation_checker.log # Scraper logs
├── subscribers.txt        # User subscriptions
└── tests/                 # Test suite
    ├── test_commands.py   # Command tests
    ├── test_bot.py       # Bot tests
    └── test_async.py     # Async tests
```

## Built With

- **Python** - Core programming language
- **Playwright** - Web automation and scraping
- **python-telegram-bot** - Telegram bot API integration
- **asyncio** - Asynchronous programming

## License

This project is for personal use only.

---

**Note**: This bot is designed for local use only. For 24/7 operation, consider deploying to a cloud service like Railway, Render, or Fly.io.
