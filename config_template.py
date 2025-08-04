import os
import json

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# Multiple users configuration
# Format: "chat_id": {"name": "User Name", "notify_no_slots": True/False, "notify_slots": True, "notify_errors": True}
# Read from environment variable with fallback
try:
    telegram_users_env = os.getenv('TELEGRAM_USERS', '{}')
    if telegram_users_env and telegram_users_env != '{}':
        TELEGRAM_USERS = json.loads(telegram_users_env)
    else:
        # Fallback to empty dict - users will be managed through /subscribe command
        TELEGRAM_USERS = {}
except (json.JSONDecodeError, TypeError) as e:
    print(f"Warning: Invalid TELEGRAM_USERS format: {e}")
    # Fallback to empty dict
    TELEGRAM_USERS = {}

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
