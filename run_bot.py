
#!/usr/bin/env python3
"""
Samezu Bot - Telegram bot for checking driving test reservations
"""

import asyncio
import logging
import os
import signal
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app_logging import configure_logging

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

configure_logging()

from reservation_checker_playwright import ReservationChecker

logger = logging.getLogger(__name__)

class SamezuBot:
    SUBSCRIBERS_FILE = 'subscribers.txt'
    TOKYO_SUBSCRIBER_SOURCES = frozenset({"samezu", "fuchu"})
    SOURCE_FACILITY_MAP = {"samezu": "鮫洲試験場", "fuchu": "府中試験場"}

    def __init__(self):
        """Initialize the bot with configuration and state management."""
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # scrape_key -> {(user_id, chat_id, check_source, show_all, use_month_navigation, force_check), ...}
        self.waiting_users = defaultdict(set)
        self.check_lock = asyncio.Lock()
        self._check_schedule_lock = asyncio.Lock()
        self._scrape_task_scheduled = False
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

        # Last result that was sent to subscribers per source — skip notification if unchanged
        self.last_notified: dict = {'tokyo': None, 'kanagawa': None}

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

    # Subscriber management methods
    def _read_subscriber_lines(self):
        try:
            with open(self.SUBSCRIBERS_FILE, 'r') as f:
                return f.readlines()
        except FileNotFoundError:
            return []

    def _write_subscriber_lines(self, lines):
        """Atomically replace subscribers file contents."""
        target = os.path.abspath(self.SUBSCRIBERS_FILE)
        directory = os.path.dirname(target) or '.'
        fd, temp_path = tempfile.mkstemp(dir=directory, prefix='.subscribers_', text=True)
        try:
            with os.fdopen(fd, 'w') as f:
                f.writelines(lines)
            os.replace(temp_path, target)
        except Exception:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise

    def _subscriber_line_for_chat_id(self, line, chat_id_str):
        stripped = line.strip()
        if not stripped:
            return False
        return stripped.startswith(f"{chat_id_str}|") or stripped == chat_id_str

    def upsert_subscriber(self, chat_id, user_info=None):
        """Insert or replace a subscriber row for chat_id."""
        chat_id_str = str(chat_id)
        try:
            kept = [
                line if line.endswith('\n') else line + '\n'
                for line in self._read_subscriber_lines()
                if not self._subscriber_line_for_chat_id(line, chat_id_str)
            ]
            if user_info:
                kept.append(f"{chat_id_str}|{user_info}\n")
            else:
                kept.append(f"{chat_id_str}\n")
            self._write_subscriber_lines(kept)
            logger.info(f"Upserted subscriber: {chat_id}")
        except Exception as e:
            logger.error(f"Failed to upsert subscriber: {e}")

    def add_subscriber(self, chat_id, user_info=None):
        """Add or update a subscriber (alias for upsert_subscriber)."""
        self.upsert_subscriber(chat_id, user_info)

    def remove_subscriber(self, chat_id):
        """Remove a chat_id from the subscribers file if present."""
        chat_id_str = str(chat_id)
        try:
            kept = [
                line if line.endswith('\n') else line + '\n'
                for line in self._read_subscriber_lines()
                if not self._subscriber_line_for_chat_id(line, chat_id_str)
            ]
            self._write_subscriber_lines(kept)
            logger.info(f"Removed subscriber: {chat_id}")
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

                if self.check_lock.locked():
                    logger.info("⏭️ Skipping scheduled check — scrape already in progress")
                    continue

                async with self.check_lock:
                    await self._run_scheduled_check(
                        checker=self.reservation_checker,
                        cache=self.cache,
                        source="tokyo",
                    )
                    await self._drain_waiting_queues_after_scrape("tokyo")

                    await self._run_scheduled_check(
                        checker=self.kanagawa_checker,
                        cache=self.kanagawa_cache,
                        source="kanagawa",
                    )
                    await self._drain_waiting_queues_after_scrape("kanagawa")

                await self._start_chained_scrapes_for_remaining_waiters()

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
        self._update_cache_after_scrape(cache, result, use_month_navigation=False)

        filtered_result = self._filter_result_by_slot_types(result, list(checker.target_slot_types))
        if "🎉" not in filtered_result:
            logger.info(f"📭 No relevant slots for {source}")
            self.last_notified[source] = None  # Reset so next open slots trigger a notification
            return

        if filtered_result == self.last_notified[source]:
            logger.info(f"🔕 Slots unchanged for {source}, skipping duplicate notification")
            return

        logger.info(f"🎉 New slots for {source}! Sending notifications...")
        self.last_notified[source] = filtered_result
        await self._send_notifications_to_subscribers(result, source=source)

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

        sources_str = ",".join(sources)
        user_info = f"{username}|{sources_str}|{subscription_type}"
        was_subscribed = str(chat_id) in [sub[0] for sub in self.get_subscribers()]
        self.upsert_subscriber(chat_id, user_info)

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

        action = "Updated" if was_subscribed else "Subscribed"
        response = (
            f"✅ {action}!\n\n"
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

        checker = self.kanagawa_checker if source == "kanagawa" else self.reservation_checker
        cache = self.kanagawa_cache if source == "kanagawa" else self.cache
        if await self._handle_cached_result(
            update, user_name, user_id, force_check, show_all, cache=cache, checker=checker,
            check_source=source, use_month_navigation=False,
        ):
            return

        scrape_key = self._scrape_key_for_check(source)
        self._enqueue_waiting_user(
            scrape_key, user_id, update.effective_chat.id, source, show_all,
            use_month_navigation=False, force_check=force_check,
        )

        if not await self._reserve_and_start_background_check(
            context, use_month_navigation=False, show_all=show_all, source=source, scrape_key=scrape_key
        ):
            logger.info(f"User {user_name} ({user_id}) queued for {scrape_key} result.")
            await update.message.reply_text(
                "⏳ A check is already running. You'll receive the result here when it finishes.",
                parse_mode='HTML',
            )
            return

        logger.info(f"User {user_name} ({user_id}) starting background check task.")

    async def check_month_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /check_month command - check using month navigation."""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name or "User"

        force_check, show_all, source = self._parse_command_args(context.args)

        logger.info(f"User {user_name} ({user_id}) issued /check_month. force={force_check}, show_all={show_all}, source={source}")

        await update.message.reply_text("🔍 Checking for available slots using month navigation...\n\nPlease wait, this may take up to 30 seconds.")
        await asyncio.sleep(0)

        checker = self.kanagawa_checker if source == "kanagawa" else self.reservation_checker
        cache = self.kanagawa_cache if source == "kanagawa" else self.cache
        if await self._handle_cached_result(
            update, user_name, user_id, force_check, show_all, cache=cache, checker=checker,
            check_source=source, use_month_navigation=True,
        ):
            return

        scrape_key = self._scrape_key_for_check(source)
        self._enqueue_waiting_user(
            scrape_key, user_id, update.effective_chat.id, source, show_all,
            use_month_navigation=True, force_check=force_check,
        )

        if not await self._reserve_and_start_background_check(
            context, use_month_navigation=True, show_all=show_all, source=source, scrape_key=scrape_key
        ):
            logger.info(f"User {user_name} ({user_id}) queued for {scrape_key} result.")
            await update.message.reply_text(
                "⏳ A check is already running. You'll receive the result here when it finishes.",
                parse_mode='HTML',
            )
            return

        logger.info(f"User {user_name} ({user_id}) starting background check task with month navigation.")

    async def _reserve_and_start_background_check(
        self, context, use_month_navigation, show_all, source, scrape_key
    ):
        """Atomically reserve a single background scrape slot and start the task."""
        async with self._check_schedule_lock:
            if self.check_lock.locked() or self._scrape_task_scheduled:
                return False
            self._scrape_task_scheduled = True

        asyncio.create_task(
            self._background_check_task(
                context,
                use_month_navigation=use_month_navigation,
                show_all=show_all,
                source=source,
                scrape_key=scrape_key,
            )
        )
        return True

    async def _telegram_send(self, chat_id, text, parse_mode='HTML'):
        """Send a Telegram message (overridable in tests)."""
        await self.application.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)

    def _scrape_key_for_check(self, check_source):
        """Map /check source arg to cache/checker bucket."""
        if check_source == "kanagawa":
            return "kanagawa"
        return "tokyo"

    def _checker_and_cache_for_scrape_key(self, scrape_key):
        if scrape_key == "kanagawa":
            return self.kanagawa_checker, self.kanagawa_cache
        return self.reservation_checker, self.cache

    def _update_cache_after_scrape(self, cache, result, use_month_navigation):
        cache['result'] = result
        cache['timestamp'] = time.time()
        cache['use_month_navigation'] = use_month_navigation

    def _is_cache_valid(self, cache):
        if not cache.get('result') or not cache.get('timestamp'):
            return False
        elapsed = time.time() - cache['timestamp']
        return elapsed < cache.get('cache_duration', CACHE_DURATION)

    def _cache_usable_for_waiter(self, cache, waiter, from_fresh_scrape):
        """Whether a queued request can be answered from cache without a new scrape."""
        _user_id, _chat_id, _check_source, _show_all, use_month, force = waiter

        if not cache.get('result'):
            return False

        if use_month != cache.get('use_month_navigation', False):
            return False

        if force:
            return from_fresh_scrape

        if not from_fresh_scrape and not self._is_cache_valid(cache):
            return False

        return True

    def _enqueue_waiting_user(
        self, scrape_key, user_id, chat_id, check_source, show_all, use_month_navigation, force_check
    ):
        self.waiting_users[scrape_key].add(
            (user_id, chat_id, check_source, show_all, use_month_navigation, force_check)
        )

    async def _deliver_to_waiting_users(self, scrape_key, from_fresh_scrape=False):
        """Send cached scrape results to waiters whose request matches the cache."""
        waiters = self.waiting_users.pop(scrape_key, None)
        if not waiters:
            return

        checker, cache = self._checker_and_cache_for_scrape_key(scrape_key)
        tasks = []
        still_waiting = set()
        delivered = 0

        for waiter in waiters:
            if not self._cache_usable_for_waiter(cache, waiter, from_fresh_scrape):
                still_waiting.add(waiter)
                continue

            _user_id, chat_id, check_source, show_all, _use_month, _force = waiter
            result_to_send = self._apply_check_filters(
                cache['result'], checker, show_all, check_source
            )
            tasks.append(self._telegram_send(chat_id, result_to_send))
            delivered += 1

        if still_waiting:
            self.waiting_users[scrape_key] |= still_waiting

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if delivered:
            logger.info(f"Sent result to {delivered} waiting users for {scrape_key}")
        if still_waiting:
            logger.info(
                f"{len(still_waiting)} waiter(s) for {scrape_key} need a matching scrape "
                f"(month={cache.get('use_month_navigation')}, fresh_only={not from_fresh_scrape})"
            )

    async def _deliver_cached_waiters_for_other_keys(self, completed_scrape_key):
        """Serve waiters on other scrape keys from valid, matching caches only."""
        for scrape_key in list(self.waiting_users.keys()):
            if scrape_key != completed_scrape_key:
                await self._deliver_to_waiting_users(scrape_key, from_fresh_scrape=False)

    async def _drain_waiting_queues_after_scrape(self, completed_scrape_key):
        """Deliver waiters compatible with the scrape that just finished, then try other caches."""
        await self._deliver_to_waiting_users(completed_scrape_key, from_fresh_scrape=True)
        await self._deliver_cached_waiters_for_other_keys(completed_scrape_key)

    async def _start_chained_scrapes_for_remaining_waiters(self):
        """Start one background scrape for the next scrape key that still has waiters."""
        for scrape_key in list(self.waiting_users.keys()):
            waiters = self.waiting_users.get(scrape_key)
            if not waiters:
                continue

            use_month_navigation = any(w[4] for w in waiters)
            show_all = any(w[3] for w in waiters)
            check_source = next(iter(waiters))[2]

            if await self._reserve_and_start_background_check(
                None,
                use_month_navigation=use_month_navigation,
                show_all=show_all,
                source=check_source,
                scrape_key=scrape_key,
            ):
                logger.info(f"Chaining background check for {scrape_key} ({len(waiters)} waiter(s))")
            return

    async def _background_check_task(
        self, context, use_month_navigation=False, show_all=False, source=None, scrape_key=None
    ):
        """Background task to perform reservation check and notify users."""
        if scrape_key is None:
            scrape_key = self._scrape_key_for_check(source)

        try:
            async with self.check_lock:
                try:
                    logger.info(
                        f"Starting background check task. scrape_key={scrape_key}, "
                        f"use_month_navigation={use_month_navigation}, show_all={show_all}, source={source}"
                    )

                    checker, cache = self._checker_and_cache_for_scrape_key(scrape_key)

                    result = await checker.run_check(
                        send_notifications=False,
                        use_month_navigation=use_month_navigation,
                        show_all=True
                    )

                    self._update_cache_after_scrape(cache, result, use_month_navigation)

                    await self._drain_waiting_queues_after_scrape(scrape_key)

                except Exception as e:
                    error_message = f"❌ Error during reservation check: {str(e)}"
                    logger.error(f"Background check task failed: {e}")

                    waiters = self.waiting_users.pop(scrape_key, None)
                    if waiters:
                        tasks = [
                            self._telegram_send(chat_id, error_message)
                            for _user_id, chat_id, _check_source, _show_all, _use_month, _force in waiters
                        ]
                        await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            async with self._check_schedule_lock:
                self._scrape_task_scheduled = False

        await self._start_chained_scrapes_for_remaining_waiters()

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

    def _subscriber_matches_source(self, subscriber_sources, notify_source):
        """Whether a subscriber should receive alerts for a scrape source."""
        if not notify_source:
            return True
        if notify_source == "kanagawa":
            return "kanagawa" in subscriber_sources
        if notify_source == "tokyo":
            return bool(set(subscriber_sources) & self.TOKYO_SUBSCRIBER_SOURCES)
        return notify_source in subscriber_sources

    def _facilities_for_subscriber_sources(self, subscriber_sources):
        """Facility names to keep in Tokyo alerts for this subscriber (None = both)."""
        tokyo_keys = [s for s in subscriber_sources if s in self.TOKYO_SUBSCRIBER_SOURCES]
        if len(tokyo_keys) >= 2:
            return None
        if len(tokyo_keys) == 1:
            return [self.SOURCE_FACILITY_MAP[tokyo_keys[0]]]
        return []

    def _facilities_for_check_source(self, check_source):
        """Facility filter for /check when source is samezu or fuchu (None = no extra filter)."""
        if check_source in self.SOURCE_FACILITY_MAP:
            return [self.SOURCE_FACILITY_MAP[check_source]]
        return None

    def _apply_check_filters(self, result, checker, show_all, check_source):
        """Apply slot-type and optional facility filters for manual /check replies."""
        if not show_all:
            result = self._filter_result_by_slot_types(result, list(checker.target_slot_types))
        facilities = self._facilities_for_check_source(check_source)
        if facilities is not None:
            result = self._filter_result_by_facilities(result, facilities)
        return result

    def _filter_result_by_facilities(self, result, keep_facilities):
        """Filter a formatted result to only include matching facility blocks."""
        if keep_facilities is None:
            return result
        if "❌ No slots" in result or "❌ Error" in result:
            return result

        if not any(
            "🏢 <b>" in line and any(f in line for f in keep_facilities)
            for line in result.split("\n")
        ):
            return f"❌ No slots found for {', '.join(keep_facilities)}"

        lines = result.split('\n')
        filtered_lines = []
        in_slot_section = False
        has_relevant_facility = False
        current_facility_kept = False
        pending_date_line = None
        pending_facility_line = None

        for line in lines:
            if any(
                h in line
                for h in [
                    "🎉 Available Reservation Slots Found!",
                    "📍",
                    "To book, click",
                    "🔗",
                ]
            ):
                filtered_lines.append(line)
                continue
            if "📅 <b>" in line and "</b>" in line:
                pending_date_line = line
                pending_facility_line = None
                in_slot_section = True
                has_relevant_facility = False
                current_facility_kept = False
                continue
            if "🏢 <b>" in line and "</b>" in line:
                pending_facility_line = line
                current_facility_kept = any(f in line for f in keep_facilities)
                continue
            if "• " in line:
                if current_facility_kept:
                    if pending_date_line is not None:
                        filtered_lines.append(pending_date_line)
                        pending_date_line = None
                    if pending_facility_line is not None:
                        filtered_lines.append(pending_facility_line)
                        pending_facility_line = None
                    filtered_lines.append(line)
                    has_relevant_facility = True
                continue
            if line.strip() == "" and in_slot_section:
                if has_relevant_facility:
                    if pending_date_line is not None:
                        filtered_lines.append(pending_date_line)
                        pending_date_line = None
                    pending_facility_line = None
                    filtered_lines.append(line)
                else:
                    pending_date_line = None
                    pending_facility_line = None
                in_slot_section = False
                continue
            if not in_slot_section or has_relevant_facility:
                filtered_lines.append(line)

        filtered_result = '\n'.join(filtered_lines)
        if not any("• " in line for line in filtered_result.split("\n")):
            return f"❌ No slots found for {', '.join(keep_facilities)}"

        summary_lines = []
        for line in filtered_result.split('\n'):
            if "📍" in line and "Facilities" in line:
                summary_lines.append(f"📍 <b>Facilities:</b> {', '.join(keep_facilities)}")
            else:
                summary_lines.append(line)
        return '\n'.join(summary_lines)

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

    @staticmethod
    def _slot_bullet_label(line):
        """Extract applicant/slot type text from a bullet line."""
        if "•" not in line:
            return None
        return line.split("•", 1)[-1].strip()

    def _filter_result_by_slot_types(self, result, keep_types):
        """Filter a formatted result string to only include lines matching keep_types.

        keep_types=None means return result unchanged.
        """
        if keep_types is None:
            return result
        if "❌ No slots" in result or "❌ Error" in result:
            return result

        keep_set = set(keep_types)
        if not any(
            (label := self._slot_bullet_label(line)) and label in keep_set
            for line in result.split("\n")
        ):
            return f"❌ No slots found for {', '.join(keep_types)}"

        lines = result.split('\n')
        filtered_lines = []
        in_slot_section = False
        has_relevant_slots = False
        pending_date_line = None
        pending_facility_line = None

        for line in lines:
            if any(
                h in line
                for h in [
                    "🎉 Available Reservation Slots Found!",
                    "📍",
                    "To book, click",
                    "🔗",
                ]
            ):
                filtered_lines.append(line)
                continue
            if "📅 <b>" in line and "</b>" in line:
                pending_date_line = line
                pending_facility_line = None
                in_slot_section = True
                has_relevant_slots = False
                continue
            if "🏢 <b>" in line and "</b>" in line:
                pending_facility_line = line
                continue
            if "• " in line:
                label = self._slot_bullet_label(line)
                if label in keep_set:
                    if pending_date_line is not None:
                        filtered_lines.append(pending_date_line)
                        pending_date_line = None
                    if pending_facility_line is not None:
                        filtered_lines.append(pending_facility_line)
                        pending_facility_line = None
                    filtered_lines.append(line)
                    has_relevant_slots = True
                continue
            if line.strip() == "" and in_slot_section:
                if has_relevant_slots:
                    if pending_date_line is not None:
                        filtered_lines.append(pending_date_line)
                        pending_date_line = None
                    pending_facility_line = None
                    filtered_lines.append(line)
                else:
                    pending_date_line = None
                    pending_facility_line = None
                in_slot_section = False
                continue
            if not in_slot_section or has_relevant_slots:
                filtered_lines.append(line)

        filtered_result = '\n'.join(filtered_lines)
        if not any(
            (label := self._slot_bullet_label(line)) and label in keep_set
            for line in filtered_result.split("\n")
        ):
            return f"❌ No slots found for {', '.join(keep_types)}"
        return filtered_result

    def _notification_messages_for_subscribers(self, result_to_send, source=None):
        """Build (chat_id, message) pairs for subscribers who should be notified."""
        messages = []
        for chat_id, user_info_raw in self.get_subscribers():
            try:
                chat_id = int(chat_id)
                username, sources, subscription_type = self.parse_subscriber_info(user_info_raw)

                if not self._subscriber_matches_source(sources, source):
                    logger.info(f"Skipping subscriber {chat_id} - not subscribed to {source}")
                    continue

                keep_types = self._resolve_keep_types(subscription_type, source)
                filtered_result = self._filter_result_by_slot_types(result_to_send, keep_types)
                if source == "tokyo":
                    facilities = self._facilities_for_subscriber_sources(sources)
                    if facilities is not None:
                        filtered_result = self._filter_result_by_facilities(filtered_result, facilities)

                if filtered_result and "❌" not in filtered_result:
                    if username and username != f"User{chat_id}":
                        tag = username if username.startswith('@') else f"@{username}"
                        notification_message = f"🔔 {tag}\n\n{filtered_result}"
                    else:
                        notification_message = filtered_result
                    messages.append((chat_id, notification_message))
                    logger.info(f"Sending {subscription_type} notification to subscriber {chat_id}")
                else:
                    logger.info(f"Skipping notification for subscriber {chat_id} - no {subscription_type} slots found")

            except Exception as e:
                logger.error(f"Failed to prepare notification for subscriber {chat_id}: {e}")

        return messages

    async def _send_notifications_to_subscribers(self, result_to_send, source=None):
        """Send notifications to subscribers, filtered by source and subscription type."""
        messages = self._notification_messages_for_subscribers(result_to_send, source=source)
        if not messages:
            if not self.get_subscribers():
                logger.warning("No subscribers to send notifications to.")
            else:
                logger.info("No notifications sent - no relevant slots for any subscribers.")
            return

        tasks = [self._telegram_send(chat_id, text) for chat_id, text in messages]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Sent notifications to {len(tasks)} subscribers.")

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

    def _cache_matches_navigation(self, cache, use_month_navigation):
        """Cache is only valid for the same navigation mode as the command."""
        return cache.get('use_month_navigation', False) == use_month_navigation

    async def _handle_cached_result(
        self, update, user_name, user_id, force_check, show_all, cache=None, checker=None,
        check_source=None, use_month_navigation=False,
    ):
        """Handle cached result response for check commands."""
        if cache is None:
            cache = self.cache
        if checker is None:
            checker = self.reservation_checker

        if (
            cache['result']
            and cache['timestamp']
            and not force_check
            and self._cache_matches_navigation(cache, use_month_navigation)
            and self._is_cache_valid(cache)
        ):
            elapsed = time.time() - cache['timestamp']
            cache_age_minutes = int(elapsed // 60)
            cache_age_seconds = int(elapsed % 60)

            cached_result = cache['result']
            if show_all and check_source not in self.SOURCE_FACILITY_MAP:
                result_to_show = cached_result
                cache_type_text = "unfiltered"
            else:
                result_to_show = self._apply_check_filters(
                    cached_result, checker, show_all, check_source
                )
                cache_type_text = "filtered"

            logger.info(f"User {user_name} ({user_id}) received cached {cache_type_text} result.")
            await update.message.reply_text(
                f"⚡ <b>Using cached result ({cache_type_text})</b>\n\n"
                f"📊 Result from {cache_age_minutes}m {cache_age_seconds}s ago:\n\n"
                f"{result_to_show}",
                parse_mode='HTML'
            )
            return True
        return False

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
