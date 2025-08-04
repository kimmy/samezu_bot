#!/usr/bin/env python3
"""
Samezu Bot - Telegram bot for checking driving test reservations
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from reservation_checker import ReservationChecker
from config_template import TELEGRAM_BOT_TOKEN, TELEGRAM_USERS, CHECK_INTERVAL

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SamezuBot:
    def remove_subscriber(self, chat_id):
        """Remove a chat_id from the subscribers file if present."""
        try:
            with open(self.SUBSCRIBERS_FILE, 'r') as f:
                lines = f.readlines()
            
            with open(self.SUBSCRIBERS_FILE, 'w') as f:
                for line in lines:
                    if not line.strip().startswith(f"{chat_id}|") and line.strip() != str(chat_id):
                        f.write(line)
            
            logger.info(f"Removed subscriber: {chat_id}")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Failed to remove subscriber: {e}")

    async def unsubscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unsubscribe command."""
        chat_id = update.effective_chat.id
        subscribers = self.get_subscribers()
        existing_ids = [sub[0] for sub in subscribers]
        
        if str(chat_id) not in existing_ids:
            await update.message.reply_text(
                "ℹ️ You are not currently subscribed.",
                parse_mode='HTML'
            )
        else:
            self.remove_subscriber(chat_id)
            await update.message.reply_text(
                "❎ You have been unsubscribed. You will no longer receive slot notifications.",
                parse_mode='HTML'
            )

    async def start_scheduler(self):
        """Start the automatic checking scheduler"""
        if self.scheduler_task is None or self.scheduler_task.done():
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info(f"🔄 Automatic checking scheduler started (interval: {CHECK_INTERVAL} seconds)")
        else:
            logger.info("🔄 Scheduler is already running")

    async def stop_scheduler(self):
        """Stop the automatic checking scheduler"""
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("🛑 Automatic checking scheduler stopped")

    async def _scheduler_loop(self):
        """Background loop that checks for slots every CHECK_INTERVAL seconds"""
        logger.info(f"⏰ Starting scheduler loop with {CHECK_INTERVAL} second intervals")
        
        while True:
            try:
                await asyncio.sleep(CHECK_INTERVAL)
                logger.info("🔄 Running scheduled check...")
                
                # Run the reservation check with notifications enabled
                result = await self.reservation_checker.run_check(send_notifications=True)
                self.update_cache(result)
                
                logger.info("✅ Scheduled check completed")
                
            except asyncio.CancelledError:
                logger.info("🛑 Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in scheduled check: {e}")
                # Continue the loop even if there's an error
                continue
    SUBSCRIBERS_FILE = 'subscribers.txt'

    def add_subscriber(self, chat_id, user_info=None):
        """Add a chat_id to the subscribers file if not already present."""
        try:
            with open(self.SUBSCRIBERS_FILE, 'a+') as f:
                f.seek(0)
                lines = f.readlines()
                existing_ids = set()
                for line in lines:
                    if '|' in line:
                        existing_id = line.split('|')[0].strip()
                    else:
                        existing_id = line.strip()
                    existing_ids.add(existing_id)
                
                if str(chat_id) not in existing_ids:
                    # Store user info for tagging
                    if user_info:
                        user_line = f"{chat_id}|{user_info}\n"
                    else:
                        user_line = f"{chat_id}\n"
                    f.write(user_line)
                    logger.info(f"Added new subscriber: {chat_id}")
        except Exception as e:
            logger.error(f"Failed to add subscriber: {e}")

    def get_subscribers(self):
        """Return a list of subscriber info (chat_id, user_info)."""
        try:
            with open(self.SUBSCRIBERS_FILE, 'r') as f:
                subscribers = []
                for line in f:
                    line = line.strip()
                    if line:
                        if '|' in line:
                            chat_id, user_info = line.split('|', 1)
                            subscribers.append((chat_id.strip(), user_info.strip()))
                        else:
                            subscribers.append((line, None))
                return subscribers
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Failed to read subscribers: {e}")
            return []

    async def subscribe_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /subscribe command."""
        chat_id = update.effective_chat.id
        user = update.effective_user
        
        # Create user info for tagging
        user_info = ""
        if user.username:
            user_info = f"@{user.username}"
        elif user.first_name:
            user_info = user.first_name
            if user.last_name:
                user_info += f" {user.last_name}"
        else:
            user_info = f"User{chat_id}"
        
        subscribers = self.get_subscribers()
        existing_ids = [sub[0] for sub in subscribers]
        
        if str(chat_id) in existing_ids:
            await update.message.reply_text(
                "ℹ️ You are already subscribed and will receive notifications when slots are found.",
                parse_mode='HTML'
            )
        else:
            self.add_subscriber(chat_id, user_info)
            await update.message.reply_text(
                f"✅ You are now subscribed! You will receive notifications when slots are found.\n\n"
                f"👤 You'll be tagged as: {user_info}",
                parse_mode='HTML'
            )
    def __init__(self):
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.reservation_checker = ReservationChecker()
        self.check_lock = asyncio.Lock()  # Only one check at a time
        self.waiting_users = set()  # Track users waiting for a check result
        self.scheduler_task = None  # Background scheduler task
        
        # Cache for check results (2 minutes)
        self.cache = {
            'result': None,
            'timestamp': None,
            'cache_duration': 120  # 2 minutes in seconds
        }
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("check", self.check_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.application.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
    
    def is_cache_valid(self):
        """Check if the cached result is still valid (within 2 minutes)."""
        if not self.cache['result'] or not self.cache['timestamp']:
            return False
        
        elapsed_time = time.time() - self.cache['timestamp']
        return elapsed_time < self.cache['cache_duration']
    
    def update_cache(self, result):
        """Update the cache with new result and timestamp."""
        self.cache['result'] = result
        self.cache['timestamp'] = time.time()
        logger.info(f"Cache updated with new result at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    def get_cache_age(self):
        """Get the age of the cached result in seconds."""
        if not self.cache['timestamp']:
            return None
        return time.time() - self.cache['timestamp']
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🎉 <b>Welcome to Samezu Bot!</b>

This bot helps you check for available driving test reservation slots.

<b>Available commands:</b>
/check - Check for available slots
/help - Show this help message

The bot will automatically notify you when slots become available.
        """
        
        await update.message.reply_text(welcome_message, parse_mode='HTML')
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"
        logger.info(f"User {user_name} ({user_id}) issued /check command.")
        # Always send the "checking" message first
        await update.message.reply_text(f"🔍 Checking for available slots...\n\nPlease wait, this may take up to 30 seconds.")
        await asyncio.sleep(0)

        # If we have a valid cache, reply immediately
        if self.is_cache_valid():
            cache_age = self.get_cache_age()
            cache_age_minutes = int(cache_age // 60)
            cache_age_seconds = int(cache_age % 60)
            logger.info(f"User {user_name} ({user_id}) received cached result before background task.")
            await update.message.reply_text(
                f"⚡ <b>Using cached result</b>\n\n"
                f"📊 Result from {cache_age_minutes}m {cache_age_seconds}s ago:\n\n"
                f"{self.cache['result']}",
                parse_mode='HTML'
            )
            logger.info(f"Using cached result for {user_name} ({user_id}) - cache age: {cache_age_minutes}m {cache_age_seconds}s")
            return

        # Add user to waiting set
        self.waiting_users.add((user_id, update.effective_chat.id))

        # If a check is already running, just return (user will get result when ready)
        if self.check_lock.locked():
            logger.info(f"User {user_name} ({user_id}) queued for result.")
            return

        # Otherwise, start a background task for the check
        logger.info(f"User {user_name} ({user_id}) starting background check task.")
        self.application.create_task(self._background_check_task(context))

    async def _background_check_task(self, context: ContextTypes.DEFAULT_TYPE):
        async with self.check_lock:
            try:
                logger.info(f"Background check task started. Notifying {len(self.waiting_users)} users.")
                # Run the reservation check
                result = await self.reservation_checker.run_check(send_notifications=False)
                self.update_cache(result)
                # Send result to all waiting users in parallel
                async def send_result(user_id, chat_id):
                    try:
                        # Clean up result message to avoid HTML parsing issues
                        clean_result = result
                        if "❌" in result and ("<" in result or ">" in result):
                            # If it's an error message with HTML, clean it up
                            clean_result = result.replace("<", "&lt;").replace(">", "&gt;")
                        
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=clean_result,
                            parse_mode='HTML'
                        )
                        logger.info(f"Sent result to user {user_id} in chat {chat_id}.")
                    except Exception as e:
                        logger.error(f"Failed to send result to user {user_id}: {e}")
                await asyncio.gather(*(send_result(user_id, chat_id) for user_id, chat_id in self.waiting_users))
            except Exception as e:
                logger.error(f"Error in background check task: {e}")
                # Notify all waiting users of the error in parallel
                async def send_error(user_id, chat_id):
                    try:
                        error_msg = f"❌ Error during check: {str(e)}"
                        # Clean up error message
                        error_msg = error_msg.replace("<", "&lt;").replace(">", "&gt;")
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=error_msg
                        )
                    except Exception as e2:
                        logger.error(f"Failed to send error to user {user_id}: {e2}")
                await asyncio.gather(*(send_error(user_id, chat_id) for user_id, chat_id in self.waiting_users))
            finally:
                self.waiting_users.clear()
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = f"""
📋 <b>Samezu Bot Help</b>

<b>Commands:</b>
/start - Welcome message
/check - Manually check for available slots
/status - Check bot status
/help - Show this help message

<b>Features:</b>
• <b>Automatic slot monitoring</b> - Checks every {CHECK_INTERVAL} seconds
• Instant notifications when slots become available
• Manual slot checking with /check command
• Concurrent checking - multiple users can check simultaneously
• Smart caching - results cached for 2 minutes to avoid repeated scraping

<b>Supported facilities:</b>
• 府中試験場 (Fuchu Test Center)
• 鮫洲試験場 (Samezu Test Center)

<b>Multi-user support:</b>
• Multiple users can use the bot simultaneously
• Each user can run their own /check command
• No waiting for other users to finish
• Use /status to check your current status

<b>Automatic checking:</b>
• Bot automatically checks for slots every {CHECK_INTERVAL} seconds
• Subscribers receive notifications when slots are found
• No manual intervention required
        """
        
        await update.message.reply_text(help_message, parse_mode='HTML')
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        # Since we now use a lock, we can't check per-user status, but we can check if a check is in progress
        check_in_progress = self.check_lock.locked()
        cache_status = ""
        if self.is_cache_valid():
            cache_age = self.get_cache_age()
            cache_age_minutes = int(cache_age // 60)
            cache_age_seconds = int(cache_age % 60)
            cache_status = f"\n⚡ <b>Cache Status:</b> Valid ({cache_age_minutes}m {cache_age_seconds}s old)"
        else:
            cache_status = "\n⚡ <b>Cache Status:</b> Expired or empty"
        if check_in_progress:
            status_message = "⏳ <b>Status</b>\n\n� A reservation check is currently in progress.\n\nPlease wait for it to complete." + cache_status
        else:
            status_message = f"✅ <b>Status</b>\n\n🟢 You're ready to use commands.\n\nYou can use /check to start a reservation check.{cache_status}"
        await update.message.reply_text(status_message, parse_mode='HTML')

class BotRunner:
    def __init__(self):
        self.bot = SamezuBot()
        self.running = True
        
    async def start(self):
        """Start the bot"""
        logger.info("🚀 Starting Samezu Bot...")
        
        # Set up signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal, stopping bot...")
            self.running = False
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Clear any existing webhook first
            await self.bot.application.bot.delete_webhook()
            logger.info("✅ Webhook cleared")
            
            await self.bot.application.initialize()
            await self.bot.application.start()
            await self.bot.application.updater.start_polling()
            
            # Start the automatic scheduler
            await self.bot.start_scheduler()
            
            logger.info("✅ Bot is running! Send /start to your bot to test it.")
            logger.info(f"⏰ Automatic checking enabled every {CHECK_INTERVAL} seconds")
            logger.info("Press Ctrl+C to stop the bot.")
            
            # Keep the bot running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            raise
        finally:
            logger.info("🛑 Stopping bot...")
            try:
                # Stop the scheduler first
                await self.bot.stop_scheduler()
                
                await self.bot.application.updater.stop()
                await self.bot.application.stop()
                await self.bot.application.shutdown()
            except:
                pass

async def main():
    """Main function"""
    runner = BotRunner()
    await runner.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)
