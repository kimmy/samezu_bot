#!/usr/bin/env python3
"""
Simple test script to verify Telegram bot configuration.
Run this before using the main reservation checker.
"""

import asyncio
import telegram
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

async def test_telegram_bot():
    """Test Telegram bot connectivity and send a test message."""
    try:
        # Create bot instance
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Test bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot connected successfully!")
        print(f"   Bot name: {bot_info.first_name}")
        print(f"   Bot username: @{bot_info.username}")
        
        # Send test message
        test_message = "🧪 <b>Test Message</b>\n\nThis is a test message from your reservation checker bot.\n\nIf you received this, your bot is configured correctly!"
        
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=test_message,
            parse_mode='HTML'
        )
        
        print(f"✅ Test message sent successfully to chat ID: {TELEGRAM_CHAT_ID}")
        print("\n🎉 Your Telegram bot is configured correctly!")
        
    except Exception as e:
        print(f"❌ Error testing Telegram bot: {e}")
        print("\nPlease check:")
        print("1. Your bot token is correct")
        print("2. Your chat ID is correct")
        print("3. You've sent a message to your bot first")
        print("4. Your internet connection is working")

if __name__ == "__main__":
    print("Testing Telegram bot configuration...")
    asyncio.run(test_telegram_bot()) 
