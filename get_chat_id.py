#!/usr/bin/env python3
"""
Script to help get your Telegram chat ID
"""

import requests
import time

BOT_TOKEN = "8208987507:AAGKj7OYN7IvVeTQX9GfECGNhUssogPvpKE"

def get_updates():
    """Get updates from Telegram API"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    return response.json()

def send_message(chat_id, message):
    """Send a message to a specific chat"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": message
    }
    response = requests.post(url, data=data)
    return response.json()

def main():
    print("🔍 Getting your chat ID...")
    print("1. Please send a message to @samezu_bot in Telegram")
    print("2. Then press Enter here to continue...")
    input()
    
    # Get updates
    updates = get_updates()
    
    if updates.get("ok") and updates["result"]:
        for update in updates["result"]:
            if "message" in update:
                chat_id = update["message"]["chat"]["id"]
                user_name = update["message"]["from"].get("first_name", "Unknown")
                print(f"✅ Found chat ID: {chat_id}")
                print(f"   User: {user_name}")
                
                # Test sending a message
                print("📤 Testing message sending...")
                result = send_message(chat_id, "🎉 Bot is working! Your chat ID is: " + str(chat_id))
                
                if result.get("ok"):
                    print("✅ Test message sent successfully!")
                    print(f"\n📝 Your chat ID is: {chat_id}")
                    print("Add this to your .env file as: TELEGRAM_CHAT_ID=" + str(chat_id))
                else:
                    print("❌ Failed to send test message")
                    print(f"Error: {result}")
                
                return chat_id
    else:
        print("❌ No messages found. Please:")
        print("1. Make sure you sent a message to @samezu_bot")
        print("2. Try again in a few seconds")
        print(f"3. Or manually check: https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")

if __name__ == "__main__":
    main() 
