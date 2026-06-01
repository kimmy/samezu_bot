
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
from reservation_checker_playwright import ReservationChecker

# Import all template values as defaults
from config_template import *

# Try to override with config values if they exist
try:
    import config
    # Override template values with config values (if they exist)
    for var in dir(config):
        if not var.startswith('_') and var.isupper():
            globals()[var] = getattr(config, var)
except ImportError:
    pass  # Use template values only

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

        # Initialize reservation checkers
        self.reservation_checker = ReservationChecker(
            target_url=TARGET_URL,
            target_facilities=TARGET_FACILITIES,
            target_slot_types=TARGET_SLOT_TYPES,
            source_name="tokyo",
        )
        self.kanagawa_checker = ReservationChecker(
            target_url=KANAGAWA_TARGET_URL,
            target_facilities=KANAGAWA_TARGET_FACILITIES,
            target_slot_types=KANAGAWA_TARGET_SLOT_TYPES,
            source_name="kanagawa",
        )

        # Per-source caches
        self.kanagawa_cache = {
            'result': None,
            'timestamp': None,
            'cache_duration': CACHE_DURATION
        }

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
        """Return a list of (chat_id, raw_user_info) tuples from subscribers file."""
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

    def parse_subscriber_info(self, user_info_raw):
        """Parse raw user_info string into (username, sources, subscription_type).

        Formats supported:
          @alice|samezu,kanagawa|relevant   (new 3-part)
          @alice|relevant                   (old 2-part — sources defaults to all)
          None / empty                      (legacy — all sources, relevant type)
        """
        if not user_info_raw:
            return None, ["samezu", "fuchu", "kanagawa"], "relevant"

        parts = user_info_raw.split('|')
        if len(parts) >= 3:
            username, sources_str, sub_type = parts[0], parts[1], parts[2]
            sources = [s.strip() for s in sources_str.split(',') if s.strip()]
        elif len(parts) == 2:
            username, sub_type = parts[0], parts[1]
            sources = ["samezu", "fuchu", "kanagawa"]  # backward compat
        else:
            username = parts[0]
            sub_type = "relevant"
            sources = ["samezu", "fuchu", "kanagawa"]

        return username, sources, sub_type

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

                await self._run_scheduled_check(
                    checker=self.reservation_checker,
                    cache=self.cache,
                    source="tokyo",
                )
                await self._run_scheduled_check(
                    checker=self.kanagawa_checker,
                    cache=self.kanagawa_cache,
                    source="kanagawa",
                )

                logger.info("✅ Scheduled check completed")

            except asyncio.CancelledError:
                logger.info("🛑 Scheduler loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in scheduled check: {e}")
                continue

    async def _run_scheduled_check(self, checker, cache, source):
        """Run one checker, update its cache, notify relevant subscribers."""
        result = await checker.run_check(send_notifications=False, show_all=True)
        cache['result'] = result
        cache['timestamp'] = time.time()

        filtered_result = await self._apply_filtering_to_cached_result(result)
        if "🎉" in filtered_result:
            logger.info(f"🎉 Found slots for {source}! Sending notifications...")
            await self._send_notifications_to_subscribers(filtered_result, source=source)
        else:
            logger.info(f"📭 No relevant slots for {source}")

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
        """Handle /subscribe command.

        Usage: /subscribe [sources] [type]
          sources: samezu, fuchu, kanagawa (space-separated; default = all three)
          type:    all, ari, nai, relevant (default = relevant)

        Examples:
          /subscribe                    → all sources, relevant type
          /subscribe kanagawa           → kanagawa only, relevant type
          /subscribe samezu fuchu       → samezu + fuchu, relevant type
          /subscribe kanagawa all       → kanagawa, all slot types
        """
        chat_id = update.effective_chat.id
        user = update.effective_user

        if user.username:
            username = f"@{user.username}"
        elif user.first_name:
            username = user.first_name
            if user.last_name:
                username += f" {user.last_name}"
        else:
            username = f"User{chat_id}"

        # Parse args into sources and type
        source_keywords = {"samezu", "fuchu", "kanagawa"}
        type_keywords = {"all", "relevant", "nai", "ari", "am", "pm", "すべて", "全て", "ない方", "ある方"}

        args_lower = [a.lower() for a in (context.args or [])]
        sources = [a for a in args_lower if a in source_keywords]
        type_args = [a for a in args_lower if a in type_keywords]

        if not sources:
            sources = ["samezu", "fuchu", "kanagawa"]

        subscription_type = "relevant"
        if type_args:
            arg = type_args[0]
            if arg in ["all", "すべて", "全て"]:
                subscription_type = "all"
            elif arg in ["nai", "ない方"]:
                subscription_type = "nai"
            elif arg in ["ari", "ある方"]:
                subscription_type = "ari"
            elif arg == "am":
                subscription_type = "am"
            elif arg == "pm":
                subscription_type = "pm"

        subscribers = self.get_subscribers()
        existing_ids = [sub[0] for sub in subscribers]

        if str(chat_id) in existing_ids:
            await update.message.reply_text(
                "ℹ️ You are already subscribed. Use /unsubscribe first to change your subscription.",
                parse_mode='HTML'
            )
            return

        sources_str = ",".join(sources)
        self.add_subscriber(chat_id, f"{username}|{sources_str}|{subscription_type}")

        sources_display = ", ".join(sources)
        is_kanagawa_only = sources == ["kanagawa"]
        type_display = {
            "all": "ALL slot types",
            "nai": "住民票のない方 only (Tokyo)",
            "ari": "住民票のある方 only (Tokyo)",
            "am": "普通車ＡＭ only (Kanagawa)",
            "pm": "普通車ＰＭ only (Kanagawa)",
            "relevant": "普通車ＡＭ &amp; ＰＭ (Kanagawa)" if is_kanagawa_only else "住民票のある方 (Tokyo)",
        }[subscription_type]

        response = (
            f"✅ Subscribed!\n\n"
            f"👤 Tagged as: {username}\n"
            f"📍 Sources: <b>{sources_display}</b>\n"
            f"📋 Slot type: <b>{type_display}</b>"
        )
        await update.message.reply_text(response, parse_mode='HTML')

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "🎉 <b>Welcome to Samezu Bot!</b>\n\n"
            "This bot monitors driving test reservation slots for Tokyo (府中・鮫洲) and Kanagawa (外国免許四輪車).\n\n"
            "<b>Available commands:</b>\n"
            "/check - Check for available slots\n"
            "/subscribe - Subscribe to notifications\n"
            "/link - Get the reservation websites\n"
            "/help - Show full help\n\n"
            "The bot checks automatically and notifies you when slots open up."
        )
        await update.message.reply_text(welcome_message, parse_mode='HTML')

    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check command.

        Usage: /check [source] [all] [force]
          source: samezu, fuchu, kanagawa (default = tokyo, i.e. samezu+fuchu)
        """
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"

        force_check, show_all, source = self._parse_command_args(context.args)

        logger.info(f"User {user_name} ({user_id}) issued /check. force={force_check}, show_all={show_all}, source={source}")

        await update.message.reply_text("🔍 Checking for available slots...\n\nPlease wait, this may take up to 30 seconds.")
        await asyncio.sleep(0)

        cache = self.kanagawa_cache if source == "kanagawa" else self.cache
        if await self._handle_cached_result(update, user_name, user_id, force_check, show_all, cache=cache):
            return

        self.waiting_users.add((user_id, update.effective_chat.id))

        if self.check_lock.locked():
            logger.info(f"User {user_name} ({user_id}) queued for result.")
            return

        logger.info(f"User {user_name} ({user_id}) starting background check task.")
        asyncio.create_task(self._background_check_task(context, use_month_navigation=False, show_all=show_all, source=source))

    async def check_month_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check_month command - check using month navigation."""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"

        force_check, show_all, source = self._parse_command_args(context.args)

        logger.info(f"User {user_name} ({user_id}) issued /check_month. force={force_check}, show_all={show_all}, source={source}")

        await update.message.reply_text("🔍 Checking for available slots using month navigation...\n\nPlease wait, this may take up to 30 seconds.")
        await asyncio.sleep(0)

        cache = self.kanagawa_cache if source == "kanagawa" else self.cache
        if await self._handle_cached_result(update, user_name, user_id, force_check, show_all, cache=cache):
            return

        self.waiting_users.add((user_id, update.effective_chat.id))

        if self.check_lock.locked():
            logger.info(f"User {user_name} ({user_id}) queued for result.")
            return

        logger.info(f"User {user_name} ({user_id}) starting background check task with month navigation.")
        asyncio.create_task(self._background_check_task(context, use_month_navigation=True, show_all=show_all, source=source))

    async def _background_check_task(self, context, use_month_navigation=False, show_all=False, source=None):
        """Background task to perform reservation check and notify users."""
        async with self.check_lock:
            try:
                logger.info(f"Starting background check task. use_month_navigation={use_month_navigation}, show_all={show_all}, source={source}")

                checker = self.kanagawa_checker if source == "kanagawa" else self.reservation_checker
                cache = self.kanagawa_cache if source == "kanagawa" else self.cache

                result = await checker.run_check(
                    send_notifications=False,
                    use_month_navigation=use_month_navigation,
                    show_all=True
                )

                cache['result'] = result
                cache['timestamp'] = time.time()

                if not show_all:
                    filtered_result = await self._apply_filtering_to_cached_result(result)
                    result_to_send = filtered_result
                else:
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
        help_message = (
            f"📋 <b>Samezu Bot Help</b>\n\n"
            f"<b>Commands:</b>\n"
            f"/check — Check for available slots (2-week navigation)\n"
            f"/check_month — Check for available slots (1-month navigation)\n"
            f"/subscribe — Subscribe to slot notifications\n"
            f"/unsubscribe — Unsubscribe from notifications\n"
            f"/link — Get reservation websites\n"
            f"/status — Bot and cache status\n"
            f"/cache — Detailed cache info\n"
            f"/help — This message\n\n"
            f"<b>Sources:</b>\n"
            f"• <b>tokyo</b> (default) — 府中試験場 &amp; 鮫洲試験場\n"
            f"• <b>kanagawa</b> — 外国免許四輪車 (普通車ＡＭ/ＰＭ)\n\n"
            f"<b>Check examples:</b>\n"
            f"• <code>/check</code> — Tokyo, relevant slots\n"
            f"• <code>/check kanagawa</code> — Kanagawa slots\n"
            f"• <code>/check all</code> — Tokyo, all slot types\n"
            f"• <code>/check kanagawa force</code> — Kanagawa, skip cache\n\n"
            f"<b>Subscribe examples:</b>\n"
            f"• <code>/subscribe</code> — All sources, relevant defaults\n"
            f"• <code>/subscribe kanagawa</code> — Kanagawa only (普通車ＡＭ/ＰＭ)\n"
            f"• <code>/subscribe samezu fuchu</code> — Tokyo only (住民票のある方)\n"
            f"• <code>/subscribe kanagawa am</code> — Kanagawa 普通車ＡＭ only\n"
            f"• <code>/subscribe kanagawa pm</code> — Kanagawa 普通車ＰＭ only\n"
            f"• <code>/subscribe nai</code> — Tokyo 住民票のない方 only\n"
            f"• <code>/subscribe ari</code> — Tokyo 住民票のある方 only\n"
            f"• <code>/subscribe all</code> — All sources, all slot types\n\n"
            f"<b>Auto-check interval:</b> every {CHECK_INTERVAL}s\n"
            f"<b>Cache duration:</b> {CACHE_DURATION}s"
        )
        await update.message.reply_text(help_message, parse_mode='HTML')

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        check_in_progress = self.check_lock.locked()

        def cache_line(label, cache):
            if cache['result'] and cache['timestamp']:
                elapsed = time.time() - cache['timestamp']
                if elapsed < cache['cache_duration']:
                    return f"✅ {label}: valid ({int(elapsed // 60)}m {int(elapsed % 60)}s old)"
            return f"❌ {label}: empty or expired"

        status = "⏳ Check in progress" if check_in_progress else "🟢 Ready"
        msg = (
            f"<b>Status</b>\n\n"
            f"{status}\n\n"
            f"<b>Cache:</b>\n"
            f"• {cache_line('Tokyo', self.cache)}\n"
            f"• {cache_line('Kanagawa', self.kanagawa_cache)}"
        )
        await update.message.reply_text(msg, parse_mode='HTML')

    async def cache_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cache command - show detailed cache information"""
        from datetime import datetime

        def format_cache(label, cache):
            if not cache['result'] or not cache['timestamp']:
                return f"<b>{label}:</b> ❌ empty"
            elapsed = time.time() - cache['timestamp']
            valid = elapsed < cache['cache_duration']
            ts = datetime.fromtimestamp(cache['timestamp']).strftime('%H:%M:%S')
            age = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
            status = "✅ valid" if valid else "❌ expired"
            return f"<b>{label}:</b> {status} — {age} old (fetched {ts})"

        message = (
            f"📊 <b>Cache Information</b>\n\n"
            f"• {format_cache('Tokyo', self.cache)}\n"
            f"• {format_cache('Kanagawa', self.kanagawa_cache)}\n\n"
            f"⏰ Duration: {CACHE_DURATION // 60} minutes"
        )
        await update.message.reply_text(message, parse_mode='HTML')

    async def link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /link command - send the reservation system website URLs"""
        link_message = (
            f"🔗 <b>Reservation Websites</b>\n\n"
            f"🗼 <b>Tokyo</b> (府中・鮫洲)\n"
            f"<a href='{TARGET_URL}'>Book Tokyo slot</a>\n\n"
            f"🏔 <b>Kanagawa</b> (外国免許四輪車)\n"
            f"<a href='{KANAGAWA_TARGET_URL}'>Book Kanagawa slot</a>"
        )
        await update.message.reply_text(link_message, parse_mode='HTML')

    def _resolve_keep_types(self, subscription_type, source):
        """Return the slot type strings to keep for a given subscription type and source.

        Tokyo types:  住民票のある方, 住民票のない方
        Kanagawa types: 普通車ＡＭ, 普通車ＰＭ

        Returns None to mean "keep all".
        """
        is_kanagawa = source == "kanagawa"
        if subscription_type == "all":
            return None
        if is_kanagawa:
            if subscription_type == "am":
                return ["普通車ＡＭ"]
            if subscription_type == "pm":
                return ["普通車ＰＭ"]
            # relevant / default for kanagawa = both AM and PM
            return list(KANAGAWA_TARGET_SLOT_TYPES)
        else:
            if subscription_type == "nai":
                return ["住民票のない方"]
            if subscription_type in ("ari", "relevant"):
                return ["住民票のある方"]
            # fallback: use configured default
            return list(TARGET_SLOT_TYPES)

    def _filter_result_by_slot_types(self, result, keep_types):
        """Filter a formatted result string to only include lines matching keep_types.

        keep_types=None means return result unchanged.
        """
        if keep_types is None:
            return result
        if "❌ No slots" in result or "❌ Error" in result:
            return result

        # If none of the target types appear at all, bail early
        if not any(t in result for t in keep_types):
            return f"❌ No slots found for {', '.join(keep_types)}"

        lines = result.split('\n')
        filtered_lines = []
        in_slot_section = False
        has_relevant_slots = False

        for line in lines:
            if any(h in line for h in ["🎉 Available Reservation Slots Found!", "📍 Facilities:", "To book, click", "🔗 Book Now"]):
                filtered_lines.append(line)
                continue
            if "📅 <b>" in line and "</b>" in line:
                in_slot_section = True
                has_relevant_slots = False
                filtered_lines.append(line)
                continue
            if "🏢 <b>" in line and "</b>" in line:
                filtered_lines.append(line)
                continue
            if "• " in line:
                if any(t in line for t in keep_types):
                    filtered_lines.append(line)
                    has_relevant_slots = True
                continue
            if line.strip() == "" and in_slot_section:
                if has_relevant_slots:
                    filtered_lines.append(line)
                in_slot_section = False
                continue
            if not in_slot_section or has_relevant_slots:
                filtered_lines.append(line)

        filtered_result = '\n'.join(filtered_lines)
        if not any(t in filtered_result for t in keep_types):
            return f"❌ No slots found for {', '.join(keep_types)}"
        return filtered_result

    async def _apply_filtering_to_cached_result(self, cached_result):
        """Apply default (relevant) filtering to a Tokyo cached result."""
        return self._filter_result_by_slot_types(cached_result, list(TARGET_SLOT_TYPES))

    async def _send_notifications_to_subscribers(self, result_to_send, source=None):
        """Send notifications to subscribers, filtered by source and subscription type."""
        subscribers = self.get_subscribers()
        if not subscribers:
            logger.warning("No subscribers to send notifications to.")
            return

        tasks = []
        for chat_id, user_info_raw in subscribers:
            try:
                chat_id = int(chat_id)
                username, sources, subscription_type = self.parse_subscriber_info(user_info_raw)

                if source and source not in sources:
                    logger.info(f"Skipping subscriber {chat_id} - not subscribed to {source}")
                    continue

                keep_types = self._resolve_keep_types(subscription_type, source)
                filtered_result = self._filter_result_by_slot_types(result_to_send, keep_types)

                if filtered_result and "❌" not in filtered_result:
                    if username and username != f"User{chat_id}":
                        tag = username if username.startswith('@') else f"@{username}"
                        notification_message = f"🔔 {tag}\n\n{filtered_result}"
                    else:
                        notification_message = filtered_result

                    task = self.application.bot.send_message(
                        chat_id=chat_id,
                        text=notification_message,
                        parse_mode='HTML'
                    )
                    tasks.append(task)
                    logger.info(f"Sending {subscription_type} notification to subscriber {chat_id}")
                else:
                    logger.info(f"Skipping notification for subscriber {chat_id} - no {subscription_type} slots found")

            except Exception as e:
                logger.error(f"Failed to send notification to subscriber {chat_id}: {e}")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Sent notifications to {len(tasks)} subscribers.")
        else:
            logger.info("No notifications sent - no relevant slots for any subscribers.")

    async def _filter_result_for_subscription(self, result, subscription_type, source=None):
        """Filter result based on subscription type and source."""
        keep_types = self._resolve_keep_types(subscription_type, source)
        return self._filter_result_by_slot_types(result, keep_types)

    # Utility methods
    def _parse_command_args(self, context_args):
        """Parse command arguments for force, filtering, and source options.

        Returns (force_check, show_all, source).
        source is "kanagawa", "samezu", "fuchu", or None (= default Tokyo).
        """
        force_check = False
        show_all = False
        source = None
        if context_args:
            args_lower = [arg.lower() for arg in context_args]
            if "force" in args_lower or "-f" in args_lower:
                force_check = True
            if "all" in args_lower or "-a" in args_lower:
                show_all = True
            if "kanagawa" in args_lower:
                source = "kanagawa"
            elif "samezu" in args_lower:
                source = "samezu"
            elif "fuchu" in args_lower:
                source = "fuchu"
        return force_check, show_all, source

    async def _handle_cached_result(self, update, user_name, user_id, force_check, show_all, cache=None):
        """Handle cached result response for check commands."""
        if cache is None:
            cache = self.cache

        if cache['result'] and cache['timestamp'] and not force_check:
            elapsed = time.time() - cache['timestamp']
            if elapsed < cache['cache_duration']:
                cache_age_minutes = int(elapsed // 60)
                cache_age_seconds = int(elapsed % 60)

                cached_result = cache['result']
                result_to_show, cache_type_text = await self._format_cache_response(
                    cached_result, show_all, cache_age_minutes, cache_age_seconds
                )

                logger.info(f"User {user_name} ({user_id}) received cached {cache_type_text} result.")
                await update.message.reply_text(
                    f"⚡ <b>Using cached result ({cache_type_text})</b>\n\n"
                    f"📊 Result from {cache_age_minutes}m {cache_age_seconds}s ago:\n\n"
                    f"{result_to_show}",
                    parse_mode='HTML'
                )
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
