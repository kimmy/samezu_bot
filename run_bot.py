
#!/usr/bin/env python3
"""
Samezu Bot - Telegram bot for checking driving test reservations
"""

import asyncio
import logging
import signal
import sys
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from reservation_checker import ReservationChecker

# Try to import from config first (for local), fallback to config_template (for Railway)
try:
    from config import (
        TELEGRAM_BOT_TOKEN, CHECK_INTERVAL,
        CACHE_DURATION, TARGET_URL
    )
except ImportError:
    from config_template import (
        TELEGRAM_BOT_TOKEN, CHECK_INTERVAL,
        CACHE_DURATION, TARGET_URL
    )

# Configure logging
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
    SUBSCRIBERS_FILE = 'subscribers.txt'

    def __init__(self):
        """Initialize the bot with configuration and state management."""
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Initialize state management
        self.subscribers = set()
        self.waiting_users = set()  # (user_id, chat_id) tuples
        self.check_lock = asyncio.Lock()
        self.scheduler_task = None  # Background scheduler task

        # Single cache for unfiltered results only
        self.cache = {
            'result': None,
            'timestamp': None,
            'cache_duration': CACHE_DURATION
        }

        # Initialize reservation checker
        self.reservation_checker = ReservationChecker()

        # Register command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("subscribe", self.subscribe_command))
        self.application.add_handler(CommandHandler("unsubscribe", self.unsubscribe_command))
        self.application.add_handler(CommandHandler("check", self.check_command))
        self.application.add_handler(CommandHandler("check_month", self.check_month_command))
        self.application.add_handler(CommandHandler("link", self.link_command))
        self.application.add_handler(CommandHandler("cache", self.cache_command))
        self.application.add_handler(CommandHandler("status", self.status_command))

    # Cache management methods
    def is_cache_valid(self):
        """Check if the cached result is still valid."""
        if not self.cache['result'] or not self.cache['timestamp']:
            return False

        elapsed_time = time.time() - self.cache['timestamp']
        return elapsed_time < self.cache['cache_duration']

    def update_cache(self, result):
        """Update the cache with new unfiltered result and timestamp."""
        self.cache['result'] = result
        self.cache['timestamp'] = time.time()
        logger.info(f"Cache updated with new unfiltered result at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    def get_cache_age(self):
        """Get the age of the cached result in seconds."""
        if not self.cache['timestamp']:
            return None
        return time.time() - self.cache['timestamp']

    # Subscriber management methods
    def add_subscriber(self, chat_id, user_info=None):
        """Add a chat_id to the subscribers file if not already present."""
        try:
            with open(self.SUBSCRIBERS_FILE, 'a+') as f:
                # Store user info for tagging
                if user_info:
                    user_line = f"{chat_id}|{user_info}\n"
                else:
                    user_line = f"{chat_id}\n"
                f.write(user_line)
                logger.info(f"Added new subscriber: {chat_id}")
        except Exception as e:
            logger.error(f"Failed to add subscriber: {e}")

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

    # Scheduler methods
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

                # Run the reservation check with notifications disabled first
                result = await self.reservation_checker.run_check(send_notifications=False, show_all=True)
                self.update_cache(result)

                # Apply filtering to check if there are relevant slots
                filtered_result = await self._apply_filtering_to_cached_result(result)

                # Only send notifications if there are actual relevant slots
                if "❌ No relevant slots found" not in filtered_result and "❌ No slots" not in filtered_result:
                    logger.info("🎉 Found relevant slots! Sending notifications to subscribers...")
                    # Send notifications to subscribers with the filtered result
                    await self._send_notifications_to_subscribers(filtered_result)
                else:
                    logger.info("📭 No relevant slots found, skipping notifications")

                logger.info("✅ Scheduled check completed")

            except asyncio.CancelledError:
                logger.info("🛑 Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in scheduled check: {e}")
                # Continue the loop even if there's an error
                continue

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

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🎉 <b>Welcome to Samezu Bot!</b>

This bot helps you check for available driving test reservation slots.

<b>Available commands:</b>
/check - Check for available slots (2-week navigation)
/check_month - Check for available slots (1-month navigation)
/link - Get the reservation system website
/cache - Show cache information
/help - Show this help message

The bot will automatically notify you when slots become available.
        """

        await update.message.reply_text(welcome_message, parse_mode='HTML')

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"

        # Parse arguments for force option and filtering
        force_check, show_all = self._parse_command_args(context.args)

        logger.info(f"User {user_name} ({user_id}) issued /check command. force={force_check}, show_all={show_all}")

        # Always send the "checking" message first
        await update.message.reply_text(f"🔍 Checking for available slots...\n\nPlease wait, this may take up to 30 seconds.")
        await asyncio.sleep(0)

        # Check if we have a valid cache
        if await self._handle_cached_result(update, user_name, user_id, force_check, show_all):
            return

        # Add user to waiting set
        self.waiting_users.add((user_id, update.effective_chat.id))

        # If a check is already running, just return (user will get result when ready)
        if self.check_lock.locked():
            logger.info(f"User {user_name} ({user_id}) queued for result.")
            return

        # Otherwise, start a background task for the check
        logger.info(f"User {user_name} ({user_id}) starting background check task.")
        asyncio.create_task(self._background_check_task(context, use_month_navigation=False, show_all=show_all))

    async def check_month_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check_month command - check using month navigation"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"

        # Parse arguments for force option and filtering
        force_check, show_all = self._parse_command_args(context.args)

        logger.info(f"User {user_name} ({user_id}) issued /check_month command. force={force_check}, show_all={show_all}")

        # Always send the "checking" message first
        await update.message.reply_text(f"🔍 Checking for available slots using month navigation...\n\nPlease wait, this may take up to 30 seconds.")
        await asyncio.sleep(0)

        # Check if we have a valid cache
        if await self._handle_cached_result(update, user_name, user_id, force_check, show_all):
            return

        # Add user to waiting set
        self.waiting_users.add((user_id, update.effective_chat.id))

        # If a check is already running, just return (user will get result when ready)
        if self.check_lock.locked():
            logger.info(f"User {user_name} ({user_id}) queued for result.")
            return

        # Otherwise, start a background task for the check with month navigation
        logger.info(f"User {user_name} ({user_id}) starting background check task with month navigation.")
        asyncio.create_task(self._background_check_task(context, use_month_navigation=True, show_all=show_all))

    async def _background_check_task(self, context, use_month_navigation=False, show_all=False):
        """Background task to perform reservation check and notify users."""
        async with self.check_lock:
            try:
                logger.info(f"Starting background check task. use_month_navigation={use_month_navigation}, show_all={show_all}")

                # Always get unfiltered results from the reservation checker
                result = await self.reservation_checker.run_check(
                    send_notifications=False,
                    use_month_navigation=use_month_navigation,
                    show_all=True  # Always get unfiltered results
                )

                # Cache the unfiltered result
                self.update_cache(result)

                # Apply filtering if needed for display
                if not show_all:
                    # Apply filtering to the unfiltered result
                    filtered_result = await self._apply_filtering_to_cached_result(result)
                    result_to_send = filtered_result
                else:
                    # Send unfiltered result
                    result_to_send = result

                # Send result to all waiting users in parallel
                if self.waiting_users:
                    tasks = []
                    for user_id, chat_id in self.waiting_users:
                        task = context.bot.send_message(
                            chat_id=chat_id,
                            text=result_to_send,
                            parse_mode='HTML'
                        )
                        tasks.append(task)

                    # Send all messages in parallel
                    await asyncio.gather(*tasks, return_exceptions=True)

                    logger.info(f"Sent result to {len(self.waiting_users)} waiting users")
                    self.waiting_users.clear()

            except Exception as e:
                error_message = f"❌ Error during reservation check: {str(e)}"
                logger.error(f"Background check task failed: {e}")

                # Send error to all waiting users
                if self.waiting_users:
                    tasks = []
                    for user_id, chat_id in self.waiting_users:
                        task = context.bot.send_message(
                            chat_id=chat_id,
                            text=error_message,
                            parse_mode='HTML'
                        )
                        tasks.append(task)

                    await asyncio.gather(*tasks, return_exceptions=True)
                    self.waiting_users.clear()

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = f"""
📋 <b>Samezu Bot Help</b>

<b>Commands:</b>
/start - Welcome message
/check - Manually check for available slots (2-week navigation)
/check_month - Manually check for available slots (1-month navigation)
/link - Get the reservation system website
/status - Check bot status
/cache - Show detailed cache information
/help - Show this help message

<b>Command Parameters:</b>
• <b>/check</b> - Check with 2-week navigation (shows only relevant slots by default)
• <b>/check all</b> - Check with 2-week navigation (shows ALL available slots)
• <b>/check force</b> - Force fresh check (ignore cache)
• <b>/check_month</b> - Check with 1-month navigation (shows only relevant slots by default)
• <b>/check_month all</b> - Check with 1-month navigation (shows ALL available slots)
• <b>/check_month force</b> - Force fresh check (ignore cache)

<b>Filtering Options:</b>
• <b>Default behavior</b> - Shows only slots for "住民票のある方" (relevant applicants)
• <b>all parameter</b> - Shows ALL available slots (both applicant types)
• <b>force parameter</b> - Ignores cache and performs fresh check

<b>Features:</b>
• <b>Automatic slot monitoring</b> - Checks every {CHECK_INTERVAL} seconds
• Instant notifications when slots become available
• Manual slot checking with /check command (2-week navigation)
• Manual slot checking with /check_month command (1-month navigation)
• Direct website access with /link command
• Concurrent checking - multiple users can check simultaneously
• Smart caching - results cached for {CACHE_DURATION} seconds to avoid repeated scraping

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

<b>Navigation options:</b>
• <b>/check</b> - Uses "2週後" (2 weeks later) button for navigation
• <b>/check_month</b> - Uses "1か月後" (1 month later) button for navigation

<b>Examples:</b>
• <code>/check</code> - Check with default filtering (relevant slots only)
• <code>/check all</code> - Check showing all available slots
• <code>/check force</code> - Force fresh check with default filtering
• <code>/check_month all force</code> - Force fresh check showing all slots with month navigation
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

    async def cache_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cache command - show detailed cache information"""
        if not self.cache['result'] or not self.cache['timestamp']: # Changed to check the single cache
            await update.message.reply_text(
                "📊 <b>Cache Information</b>\n\n"
                "❌ <b>No cached results available</b>\n\n"
                "The unfiltered cache is empty.",
                parse_mode='HTML'
            )
            return

        # Format timestamp
        from datetime import datetime

        # Get cache duration in minutes
        cache_duration_minutes = CACHE_DURATION // 60

        # Create detailed message
        message = f"📊 <b>Cache Information</b>\n\n"
        message += f"⏰ <b>Cache Duration:</b> {cache_duration_minutes} minutes\n\n"

        # Cache info
        cache_time = datetime.fromtimestamp(self.cache['timestamp'])
        cache_formatted = cache_time.strftime('%Y-%m-%d %H:%M:%S')
        cache_age = self.get_cache_age()
        cache_minutes = int(cache_age // 60) if cache_age else 0
        cache_seconds = int(cache_age % 60) if cache_age else 0
        cache_status = "✅ Valid" if self.is_cache_valid() else "❌ Expired"

        message += f"🔍 <b>Unfiltered Cache:</b>\n"
        message += f"   📅 <b>Time:</b> {cache_formatted}\n"
        message += f"   ⏱️ <b>Age:</b> {cache_minutes}m {cache_seconds}s\n"
        message += f"   📊 <b>Status:</b> {cache_status}\n\n"

        message += "<b>Cache Types:</b>\n"
        message += "• <b>Unfiltered:</b> Used for /check and /check_month (all available slots)\n\n"
        message += "<b>Note:</b> The unfiltered cache is independent and has its own 2-minute expiration."

        await update.message.reply_text(message, parse_mode='HTML')

    async def link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /link command - send the reservation system website URL"""
        link_message = f"""
🔗 <b>Reservation System Website</b>

📋 <b>Tokyo Police Department Driving Test Reservation System</b>

🌐 <b>Website:</b> {TARGET_URL}

💡 <b>Note:</b> You can visit this website directly to check for available slots manually.
        """

        await update.message.reply_text(link_message, parse_mode='HTML')

    async def _apply_filtering_to_cached_result(self, cached_result):
        """Apply filtering to cached unfiltered results to show only relevant slots."""
        try:
            # If the cached result is already filtered or has no slots, return as is
            if "❌ No slots" in cached_result or "❌ Error" in cached_result:
                return cached_result

            # If the cached result doesn't contain slots for "住民票のない方", it's already filtered
            if "住民票のない方" not in cached_result:
                return cached_result

            # Parse the cached result to extract slots and filter them
            lines = cached_result.split('\n')
            filtered_lines = []
            in_slot_section = False
            current_date = None
            current_facility = None
            has_relevant_slots = False

            for line in lines:
                # Keep header lines
                if any(header in line for header in ["🎉 Available Reservation Slots Found!", "📍 Facilities:", "To book, click", "🔗 Book Now"]):
                    filtered_lines.append(line)
                    continue

                # Keep date headers
                if "📅 <b>" in line and "</b>" in line:
                    current_date = line
                    in_slot_section = True
                    has_relevant_slots = False
                    filtered_lines.append(line)
                    continue

                # Keep facility headers
                if "🏢 <b>" in line and "</b>" in line:
                    current_facility = line
                    filtered_lines.append(line)
                    continue

                # Filter slot lines - only keep "住民票のある方"
                if "• " in line and "住民票" in line:
                    if "住民票のある方" in line:
                        filtered_lines.append(line)
                        has_relevant_slots = True
                    # Skip "住民票のない方" lines
                    continue

                # Add empty line after facility if it had relevant slots
                if line.strip() == "" and in_slot_section and has_relevant_slots:
                    filtered_lines.append(line)
                    in_slot_section = False
                    continue

                # Keep other lines
                if not in_slot_section or has_relevant_slots:
                    filtered_lines.append(line)

            # Join the filtered lines
            filtered_result = '\n'.join(filtered_lines)

            # If no relevant slots found, return the "no relevant slots" message
            if "住民票のある方" not in filtered_result:
                return "❌ No relevant slots found (only showing 住民票のある方)"

            return filtered_result

        except Exception as e:
            logger.error(f"Error applying filtering to cached result: {e}")
            # If filtering fails, return the original cached result
            return cached_result

    async def _send_notifications_to_subscribers(self, result_to_send):
        """Send notifications to all subscribers."""
        subscribers = self.get_subscribers()
        if not subscribers:
            logger.warning("No subscribers to send notifications to.")
            return

        tasks = []
        for chat_id, user_info in subscribers:
            try:
                # Ensure the chat_id is an integer for send_message
                chat_id = int(chat_id)

                # Create notification message with user tag if available
                if user_info and user_info != f"User{chat_id}":
                    notification_message = f"🔔 @{user_info}\n\n{result_to_send}"
                else:
                    notification_message = result_to_send

                task = self.application.bot.send_message(
                    chat_id=chat_id,
                    text=notification_message,
                    parse_mode='HTML'
                )
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to send notification to subscriber {chat_id}: {e}")

        # Send all messages in parallel
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Sent notifications to {len(subscribers)} subscribers.")

    # Utility methods
    def _parse_command_args(self, context_args):
        """Parse command arguments for force and filtering options."""
        force_check = False
        show_all = False
        if context_args:
            args_lower = [arg.lower() for arg in context_args]
            if "force" in args_lower or "-f" in args_lower:
                force_check = True
            if "all" in args_lower or "-a" in args_lower:
                show_all = True
        return force_check, show_all

    async def _handle_cached_result(self, update, user_name, user_id, force_check, show_all):
        """Handle cached result response for check commands."""
        if self.is_cache_valid() and not force_check:
            cache_age = self.get_cache_age()
            cache_age_minutes = int(cache_age // 60)
            cache_age_seconds = int(cache_age % 60)

            # Get cached result and apply filtering if needed
            cached_result = self.cache['result']
            result_to_show, cache_type_text = await self._format_cache_response(
                cached_result, show_all, cache_age_minutes, cache_age_seconds
            )

            logger.info(f"User {user_name} ({user_id}) received cached {cache_type_text} result before background task.")
            await update.message.reply_text(
                f"⚡ <b>Using cached result ({cache_type_text})</b>\n\n"
                f"📊 Result from {cache_age_minutes}m {cache_age_seconds}s ago:\n\n"
                f"{result_to_show}",
                parse_mode='HTML'
            )
            logger.info(f"Using cached {cache_type_text} result for {user_name} ({user_id}) - cache age: {cache_age_minutes}m {cache_age_seconds}s")
            return True
        return False

    async def _format_cache_response(self, cached_result, show_all, cache_age_minutes, cache_age_seconds):
        """Format cached result response with appropriate filtering."""
        if not show_all:
            # Apply filtering to cached unfiltered results
            filtered_result = await self._apply_filtering_to_cached_result(cached_result)
            result_to_show = filtered_result
            cache_type_text = "filtered"
        else:
            # Show unfiltered results
            result_to_show = cached_result
            cache_type_text = "unfiltered"

        return result_to_show, cache_type_text

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
