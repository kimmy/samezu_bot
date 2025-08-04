import os
import json

# Telegram Bot Configuration
# Set this as a GitHub secret: TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "YOUR_BOT_TOKEN_HERE")

# Multiple users configuration
# Set this as a GitHub secret: TELEGRAM_USERS (JSON string)
# Format: "chat_id": {"name": "User Name", "notify_no_slots": True/False, "notify_slots": True, "notify_errors": True}
default_users = {
    "YOUR_CHAT_ID_HERE": {
        "name": "Your Name",
        "notify_no_slots": True,  # Send "no slots" messages
        "notify_slots": True,      # Send detailed slot notifications
        "notify_errors": True      # Send error notifications
    }
}

try:
    TELEGRAM_USERS = json.loads(os.getenv('TELEGRAM_USERS', json.dumps(default_users)))
except (json.JSONDecodeError, TypeError):
    TELEGRAM_USERS = default_users

# Target Website Configuration
TARGET_URL = "https://www.samezu.com/reservation/"

# Target facilities to check
TARGET_FACILITIES = ["Tennis Court", "Badminton Court", "Squash Court"]

# Check interval in seconds
CHECK_INTERVAL = 300  # 5 minutes

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = "reservation_checker.log"

# Browser Configuration
BROWSER_TYPE = "chromium"
HEADLESS = True
TIMEOUT = 30000  # 30 seconds 
