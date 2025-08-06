
# =====================
# Config for Samezu Bot
#
# - For local dev: copy this file to config.py and fill in real values below.
# - For Railway: set environment variables in dashboard, do not use config.py.
# - This file is safe to commit (no secrets).
# =====================

import os

# Telegram Bot Configuration
# Use environment variable if available, otherwise use placeholder
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', "YOUR_BOT_TOKEN_HERE")

# Target Website Configuration
TARGET_URL = "https://www.keishicho-gto.metro.tokyo.lg.jp/keishicho-u/reserve/offerList_detail?tempSeq=445&accessFrom=offerList"

# Target facilities to check
TARGET_FACILITIES = ["府中試験場", "鮫洲試験場"]

# Filtering Configuration
# Set to True to show only slots for "住民票のある方" (relevant applicants)
# Set to False to show all available slots
SHOW_ONLY_RELEVANT_APPLICANTS = True

# Check interval in seconds
CHECK_INTERVAL = 300  # 5 minutes

# Cache duration in seconds
CACHE_DURATION = 120  # 2 minutes

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FILE = "reservation_checker.log"

# Browser Configuration
HEADLESS = True  # Set to False for debugging
TIMEOUT = 30000  # 30 seconds timeout
