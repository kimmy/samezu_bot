import os
import json

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "8208987507:AAGKj7OYN7IvVeTQX9GfECGNhUssogPvpKE")

# Multiple users configuration
# Format: "chat_id": {"name": "User Name", "notify_no_slots": True/False, "notify_slots": True, "notify_errors": True}
# Read from environment variable or use default
default_users = {
    "117386608": {
        "name": "Kim",
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
TARGET_URL = "https://www.keishicho-gto.metro.tokyo.lg.jp/keishicho-u/reserve/offerList_detail?tempSeq=445&accessFrom=offerList"

# Target facilities to check
TARGET_FACILITIES = ["府中試験場", "鮫洲試験場"]

# Check interval in seconds
CHECK_INTERVAL = 300  # 5 minutes

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = "reservation_checker.log"

# Browser Configuration
HEADLESS = True  # Set to False for debugging
TIMEOUT = 30000  # 30 seconds timeout 