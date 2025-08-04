
# =====================
# Config for Samezu Bot
#
# - For local dev: copy this file to config.py and fill in real values below.
# - For Railway: set environment variables in dashboard, do not use config.py.
# - This file is safe to commit (no secrets).
# =====================

import os
import json

# Telegram Bot Configuration
# Use environment variable if available, otherwise use placeholder
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "YOUR_BOT_TOKEN_HERE")

# Multiple users configuration
# Format: "chat_id": {"name": "User Name", "notify_no_slots": True/False, "notify_slots": True, "notify_errors": True}
# Read from environment variable or use empty dict
try:
    # Try to get users from environment variable first
    telegram_users_env = os.getenv('TELEGRAM_USERS')
    if telegram_users_env:
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
