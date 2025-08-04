import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
# Replace with your actual bot token
TELEGRAM_BOT_TOKEN = "your_bot_token_here"

# Multiple users configuration
# Add your users here - replace with actual chat IDs and names
TELEGRAM_USERS = {
    # Example user (replace with real data):
    # "123456789": {
    #     "name": "Example User",
    #     "notify_no_slots": True,  # Send "no slots" messages
    #     "notify_slots": True,      # Send detailed slot notifications
    #     "notify_errors": True      # Send error notifications
    # }
}

# Target Website Configuration
TARGET_URL = "https://www.keishicho-gto.metro.tokyo.lg.jp/keishicho-u/reserve/offerList_detail?tempSeq=445&accessFrom=offerList"
TARGET_FACILITIES = ["鮫洲試験場", "府中試験場"]  # Check both facilities

# Browser Configuration
HEADLESS = True  # Set to False for debugging
TIMEOUT = 30000  # 30 seconds timeout 
