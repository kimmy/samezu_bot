# Tokyo Police Department Reservation Checker

Automatically checks for available reservation slots at 鮫洲試験場 (Samezu Testing Center) and sends Telegram notifications when slots are found.

## Features

- 🔍 **Automated Web Scraping**: Uses Playwright to navigate the reservation website
- 📅 **Multi-Week Scanning**: Automatically clicks through all available weeks
- 🎯 **Targeted Search**: Focuses only on 鮫洲試験場 facility
- 📱 **Telegram Notifications**: Sends immediate alerts when slots are available
- 📊 **Detailed Logging**: Comprehensive logging for debugging and monitoring
- ⚡ **Fast & Reliable**: Optimized for speed and reliability

## Requirements

- Python 3.8 or higher
- Internet connection
- Telegram Bot Token and Chat ID

## Installation

### 1. Clone or Download the Project

```bash
# If using git
git clone <repository-url>
cd reservation-checker

# Or simply download the files to a folder
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

### 4. Set Up Telegram Bot

1. **Create a Telegram Bot**:
   - Message @BotFather on Telegram
   - Send `/newbot`
   - Follow the instructions to create your bot
   - Save the bot token

2. **Get Your Chat ID**:
   - Send a message to your bot
   - Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - Find your `chat_id` in the response

### 5. Configure Your Bot

**Option 1: Quick Setup (Recommended)**
```bash
python setup.py
```
This will create a `config.py` file from the template. Then edit it with your bot token and chat IDs.

**Option 2: Manual Setup**
```bash
cp config_template.py config.py
```
Then edit `config.py` with your actual bot token and chat IDs.

**Security Note**: `config.py` is in `.gitignore` and won't be committed to git, keeping your private information safe.

## Usage

### Manual Run

```bash
# Activate virtual environment
source venv/bin/activate

# Run the reservation checker
python reservation_checker.py
```

### Manage Users

```bash
# Add/remove users and change notification preferences
python manage_users.py
```

### Automated Scheduling

#### Linux/macOS (Cron)

1. Make the script executable:
```bash
chmod +x reservation_checker.py
```

2. Edit crontab:
```bash
crontab -e
```

3. Add a line to run every 30 minutes:
```bash
*/30 * * * * cd /path/to/reservation-checker && python reservation_checker.py
```

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., every 30 minutes)
4. Set action: Start a program
5. Program: `python`
6. Arguments: `reservation_checker.py`
7. Start in: `C:\path\to\reservation-checker`

## Configuration

Edit `config.py` to customize:

- `HEADLESS`: Set to `False` for debugging (shows browser window)
- `TIMEOUT`: Adjust timeout for page loading
- `TARGET_FACILITY`: Change target facility if needed

## How It Works

1. **Navigation**: Opens the reservation website in a headless browser
2. **Week Scanning**: Clicks through all available weeks using the "2週後＞" button
3. **Row Filtering**: Finds all rows for 鮫洲試験場 facility
4. **Availability Check**: Looks for `aria-label="予約可能"` in SVG elements
5. **Notification**: Sends formatted Telegram message with available slots

## Output Format

When slots are found, you'll receive a Telegram message like:

```
🎉 Available Reservation Slots Found!

📍 Facility: 鮫洲試験場

📅 2024年1月15日
   • 住民票のある方
   • 住民票のない方

📅 2024年1月16日
   • 住民票のある方

🔗 Book Now
```

## Logging

The script creates a `reservation_checker.log` file with detailed information about:
- Page navigation
- Available slots found
- Errors and exceptions
- Telegram message status

## Troubleshooting

### Common Issues

1. **"No module named 'playwright'"**
   ```bash
   pip install playwright
   playwright install chromium
   ```

2. **"No module named 'telegram'"**
   ```bash
   pip install python-telegram-bot
   ```

3. **Browser not launching**
   - Check if Playwright browsers are installed
   - Try setting `HEADLESS = False` in config.py for debugging

4. **Telegram message not sending**
   - Verify bot token and chat ID in .env file
   - Check internet connection
   - Ensure bot has permission to send messages

### Debug Mode

Set `HEADLESS = False` in `config.py` to see the browser window and debug issues.

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- The bot token gives access to your Telegram bot - keep it private
- The script runs in a sandboxed browser environment

## License

This project is for personal use. Please respect the target website's terms of service.

## Built With

- **Cursor** - AI-powered code editor that helped build this project
- **Python** - Core programming language
- **Playwright** - Web automation and scraping
- **python-telegram-bot** - Telegram bot API integration

## Support

For issues or questions:
1. Check the log file for error details
2. Enable debug mode by setting `HEADLESS = False`
3. Verify your Telegram bot configuration 
