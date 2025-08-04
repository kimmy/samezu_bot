# Samezu Bot

A Python-based reservation checker for Samezu facilities that sends Telegram notifications when slots become available.

## Features

- 🔍 **Automated Checking**: Monitors multiple facilities for available slots
- 📱 **Telegram Notifications**: Sends instant notifications when slots are found
- ⚙️ **Flexible Configuration**: Support for multiple users with customizable notification preferences
- 🔒 **Secure**: Uses GitHub secrets for sensitive data
- 🚀 **Easy Setup**: Simple installation and configuration process

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

### Option 1: GitHub Secrets (Recommended for Production)

1. **Go to your GitHub repository**
2. **Navigate to Settings > Secrets and variables > Actions**
3. **Add these secrets:**

   **TELEGRAM_BOT_TOKEN:**
   ```
   your_bot_token_here
   ```

   **TELEGRAM_USERS:**
   ```json
   {
     "YOUR_CHAT_ID": {
       "name": "Your Name",
       "notify_no_slots": true,
       "notify_slots": true,
       "notify_errors": true
     }
   }
   ```

### Option 2: Local Development

1. **Run the setup script:**
   ```bash
   python setup.py
   ```

2. **Update config.py with your credentials:**
   - Replace `YOUR_BOT_TOKEN_HERE` with your actual bot token
   - Replace `YOUR_CHAT_ID_HERE` with your chat ID
   - Update the user name and notification preferences

3. **Or create a .env file:**
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_USERS={"YOUR_CHAT_ID": {"name": "Your Name", "notify_no_slots": true, "notify_slots": true, "notify_errors": true}}
   ```

## Dual Environment Setup: Local vs Railway

### Local Development
- Copy `config_template.py` to `config.py` and fill in your real credentials (do NOT commit `config.py`).
- Or, set environment variables in your shell for local testing.
- All scripts import `config` (which is your local copy).

### Railway Deployment
- Do NOT use `config.py` (it is not in the repo and not needed).
- Set all secrets (e.g., `TELEGRAM_BOT_TOKEN`, `TELEGRAM_USERS`) as environment variables in the Railway dashboard.
- Railway will use `config_template.py` (which reads from environment variables).

### Security
- Never commit real credentials to Git.
- `config.py` is in `.gitignore` and only exists locally.

### Example
- For local: `cp config_template.py config.py` and edit values.
- For Railway: set env vars only, no file changes needed.

---

## Usage

### Basic Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run the reservation checker
python reservation_checker.py
```

### Manage Users

```bash
# Add, remove, or update users
python manage_users.py
```

### Test Your Bot

```bash
# Test if your bot is working
python test_bot.py
```

## Configuration Options

### User Notification Preferences

Each user can configure their notification preferences:

- `notify_no_slots`: Receive "no slots" messages (default: true)
- `notify_slots`: Receive detailed slot notifications (default: true)
- `notify_errors`: Receive error notifications (default: true)

### Check Interval

Modify `CHECK_INTERVAL` in `config.py` to change how often the bot checks for slots (default: 300 seconds = 5 minutes).

## Scheduling

### Linux/macOS (cron)

```bash
# Edit crontab
crontab -e

# Add this line to run every 5 minutes
*/5 * * * * cd /path/to/samezu_bot && /path/to/venv/bin/python reservation_checker.py
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to run every 5 minutes
4. Set action to run: `python reservation_checker.py`

## Troubleshooting

### Common Issues

1. **"externally-managed-environment" error:**
   - Use virtual environment: `python3 -m venv venv && source venv/bin/activate`

2. **Playwright browser issues:**
   - Reinstall browsers: `playwright install chromium`

3. **Telegram bot not responding:**
   - Check your bot token in config.py
   - Test with: `python test_bot.py`

4. **SSH push issues:**
   - Verify SSH key is added: `ssh-add -l`
   - Test connection: `ssh -T git@github.com`

### Logs

Check `reservation_checker.log` for detailed error messages and debugging information.

## Security

- ✅ Sensitive data stored in GitHub secrets
- ✅ config.py excluded from Git (.gitignore)
- ✅ Environment variables for local development
- ✅ Template-based configuration

## Built With

- **Cursor** - AI-powered code editor that helped build this project
- **Python** - Core programming language
- **Playwright** - Web automation and scraping
- **python-telegram-bot** - Telegram bot API integration

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for personal use only.
