#!/usr/bin/env python3
"""
Tokyo Police Department Reservation Checker
Automatically checks for available reservation slots at 鮫洲試験場
and sends Telegram notifications when slots are found.
"""

import asyncio
import logging
import os
import re
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from playwright.async_api import async_playwright, Page

from domain import (
    CheckResult,
    Slot,
    dedupe_slots,
    filter_slots,
    format_check_message,
)
from telegram import Bot
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

DATE_MD_PATTERN = re.compile(r'\d{1,2}/\d{1,2}')
FULL_DATE_PATTERN = re.compile(r'(\d{4})年(\d{2})月(\d{2})日')

logger = logging.getLogger('reservation_checker_playwright')

class ReservationChecker:
    def __init__(self, target_url=None, target_facilities=None, target_slot_types=None, source_name="tokyo"):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.available_slots = []
        self.target_url = target_url or TARGET_URL
        self.target_facilities = target_facilities or TARGET_FACILITIES
        self.target_slot_types = target_slot_types or TARGET_SLOT_TYPES
        self.source_name = source_name

    async def send_telegram_message(self, message: str):
        """Send to every line in subscribers.txt (legacy). Production must use run_bot.py instead."""
        try:
            with open('subscribers.txt', 'r') as f:
                subscribers = []
                for line in f:
                    line = line.strip()
                    if line:
                        if '|' in line:
                            chat_id, user_info = line.split('|', 1)
                            subscribers.append((chat_id.strip(), user_info.strip()))
                        else:
                            subscribers.append((line, None))
        except FileNotFoundError:
            subscribers = []
        except Exception as e:
            logger.error(f"Failed to read subscribers: {e}")
            subscribers = []

        for chat_id, user_info in subscribers:
            try:
                # Add user mention to the message
                if user_info:
                    tagged_message = f"🔔 {user_info}\n\n{message}"
                else:
                    tagged_message = message

                await self.bot.send_message(
                    chat_id=int(chat_id),
                    text=tagged_message,
                    parse_mode='HTML'
                )
                logger.info(f"Telegram message sent successfully to subscriber {chat_id} ({user_info})")
            except Exception as e:
                logger.error(f"Failed to send Telegram message to subscriber {chat_id}: {e}")

    async def wait_for_page_load(self, page: Page):
        """Wait for the page to load completely, handling Cloudflare waiting room."""
        # Wait up to 3 minutes total for Cloudflare waiting room to pass
        max_wait = 180000
        poll_interval = 5000

        elapsed = 0
        while elapsed < max_wait:
            try:
                title = await page.title()
            except Exception:
                # Page navigated mid-call (e.g. Cloudflare redirect) — retry
                await page.wait_for_timeout(1000)
                elapsed += 1000
                continue
            if 'Waiting Room' in title:
                logger.info(f"Cloudflare waiting room detected, waiting... ({elapsed // 1000}s elapsed)")
                await page.wait_for_timeout(poll_interval)
                elapsed += poll_interval
                continue

            # We're past the waiting room — wait for the actual table
            try:
                await page.wait_for_selector('table', timeout=TIMEOUT)

                # Wait for any loading indicators to disappear
                try:
                    await page.wait_for_selector('.loading, .spinner, [aria-busy="true"]',
                                              state='hidden', timeout=LOADING_INDICATOR_TIMEOUT)
                except:
                    pass

                await page.wait_for_timeout(DYNAMIC_CONTENT_WAIT)

                facility_elements = await page.query_selector_all('td')
                if not facility_elements:
                    raise Exception("No table data found on page")
                return

            except Exception as e:
                logger.error(f"Timeout waiting for page load: {e}")
                raise

        raise Exception("Timed out waiting for Cloudflare waiting room to pass (3 minutes)")

    @staticmethod
    def _normalize_label(text: str) -> str:
        return ' '.join(text.strip().split())

    @classmethod
    def _applicant_type_matches(cls, applicant_type: str, target_types: List[str]) -> bool:
        return cls._normalize_label(applicant_type) in target_types

    @classmethod
    def _resolve_calendar_row(
        cls,
        first_text: str,
        second_text: str,
        current_facility: Optional[str],
        target_facilities: List[str],
    ) -> Optional[Tuple[str, str, str, int]]:
        """Map a table row to facility, slot type, and where date cells start.

        Kanagawa (and similar layouts) use rowspan on the facility cell, so only the
        first slot-type row includes the facility name; follow-on rows have slot type
        in the first column.
        """
        first_text = cls._normalize_label(first_text)
        second_text = cls._normalize_label(second_text)

        for facility in target_facilities:
            if cls._normalize_label(facility) in first_text:
                return facility, facility, second_text, 2

        if current_facility:
            return current_facility, current_facility, first_text, 1

        return None

    async def _collect_date_headers(self, rows) -> List[str]:
        """Find the calendar header row (cells look like MM/DD)."""
        for row in rows:
            cells = await row.query_selector_all('td')
            if len(cells) < 3:
                continue
            headers = []
            for cell in cells:
                date_text = await cell.text_content()
                if not date_text or not date_text.strip():
                    continue
                clean_date = self._normalize_label(date_text)
                if DATE_MD_PATTERN.search(clean_date):
                    headers.append(clean_date)
            if len(headers) >= 3:
                return headers
        return []

    async def _date_for_slot_cell(self, cell, index: int, date_headers: List[str]) -> str:
        if index < len(date_headers):
            return date_headers[index]

        sr_only = await cell.query_selector('.sr-only')
        if sr_only:
            sr_text = await sr_only.text_content()
            if sr_text:
                date_match = FULL_DATE_PATTERN.search(sr_text)
                if date_match:
                    _year, month, day = date_match.groups()
                    return f"{month}/{day}"

        return f"Unknown date {index + 1}"

    async def get_available_dates(self, page: Page) -> List[Slot]:
        """Extract available dates from the current page."""
        available_slots = []

        try:
            rows = await page.query_selector_all('tr')
            date_headers = await self._collect_date_headers(rows)

            if date_headers:
                logger.info(f"📅 Checking dates: {date_headers[0]} to {date_headers[-1]}")
            else:
                logger.info("📅 Date range: Unable to determine")

            current_facility = None
            for row in rows:
                row_cells = await row.query_selector_all('th, td')
                if len(row_cells) < 2:
                    continue

                first_text = await row_cells[0].text_content() or ""
                second_text = await row_cells[1].text_content() or ""
                resolved = self._resolve_calendar_row(
                    first_text, second_text, current_facility, self.target_facilities
                )
                if not resolved:
                    continue

                current_facility, target_facility, applicant_type, date_start = resolved
                applicant_type = self._normalize_label(applicant_type) or "Unknown"
                date_cells = row_cells[date_start:]
                if not date_cells:
                    continue

                for i, cell in enumerate(date_cells):
                    date_text = await self._date_for_slot_cell(cell, i, date_headers)

                    # Check for available slot
                    svg = await cell.query_selector('svg')
                    if svg:
                        aria_label = await svg.get_attribute('aria-label')
                        if aria_label == "予約可能":
                            available_slots.append(
                                Slot(
                                    date=date_text,
                                    facility=target_facility,
                                    applicant_type=applicant_type,
                                )
                            )
                            logger.info(f"✅ Found available slot: {date_text} - {target_facility} - {applicant_type}")
                        elif aria_label == "空き無":
                            logger.debug(f"❌ No availability: {date_text} - {applicant_type}")
                        elif aria_label == "時間外":
                            logger.debug(f"⏰ Outside hours: {date_text} - {applicant_type}")

        except Exception as e:
            logger.error(f"Error extracting available dates: {e}")

        return available_slots

    async def _check_periods(self, page: Page, navigation_type: str, max_periods: int = 20) -> List[Dict]:
        """Core method to check all available periods for reservations."""
        all_available_slots = []
        period_count = 0

        while period_count < max_periods:
            period_count += 1
            logger.info(f"🔄 Checking {navigation_type} {period_count}")

            # Wait for page to load
            await self.wait_for_page_load(page)

            # Check if we've reached the end of available dates
            if await self.is_end_of_available_dates(page):
                logger.info("🏁 Detected end of available dates")
                break

            # Get available slots from current page
            current_slots = await self.get_available_dates(page)
            all_available_slots.extend(current_slots)

            # Log summary for this period
            if current_slots:
                logger.info(f"🎯 {navigation_type.capitalize()} {period_count}: Found {len(current_slots)} available slots")
            else:
                logger.info(f"📭 {navigation_type.capitalize()} {period_count}: No available slots found")

            # Check for navigation button
            try:
                if navigation_type == "month":
                    # Use "1か月後" (1 month later) button
                    next_button = await page.query_selector('input[value="1か月後＞"]')
                else:
                    # Use "2週後" (2 weeks later) button
                    next_button = await page.query_selector('input[value="2週後＞"]')

                if not next_button:
                    logger.info(f"Next {navigation_type} button not found - reached end of available dates")
                    break

                # Check if button is disabled or has no-click attribute
                is_disabled = await next_button.get_attribute('disabled')
                is_clickable = await next_button.is_enabled()
                aria_label = await next_button.get_attribute('aria-label')

                # Log button status for debugging
                logger.info(f"🔘 Next {navigation_type} button status - disabled: {is_disabled}, enabled: {is_clickable}, aria-label: {aria_label}")

                # If button is disabled or not clickable, we've reached the end
                if is_disabled or not is_clickable:
                    logger.info(f"Next {navigation_type} button is disabled/not clickable - reached end of available dates")
                    break

                # Try to click the button
                await next_button.click()
                logger.info(f"✅ Successfully clicked next {navigation_type} button")

                # Wait for page transition with better error handling
                try:
                    await page.wait_for_timeout(PAGE_TRANSITION_WAIT)  # Configurable wait time
                    # Additional check to ensure page loaded
                    await page.wait_for_selector('table', timeout=TIMEOUT)
                except Exception as e:
                    logger.warning(f"Page transition timeout: {e}")
                    # Continue anyway as the page might have loaded

            except Exception as e:
                logger.info(f"Error with next {navigation_type} button or reached end: {e}")
                break

        # Final summary
        logger.info(f"📊 SUMMARY: Checked {period_count} {navigation_type}s, found {len(all_available_slots)} total available slots")

        all_available_slots = list(dedupe_slots(all_available_slots))

        if all_available_slots:
            logger.info("🎉 Available slots found:")
            slots_by_facility: dict = {}
            for slot in all_available_slots:
                slots_by_facility.setdefault(slot.facility, []).append(slot)

            for facility, slots in slots_by_facility.items():
                logger.info(f"   🏢 {facility}: {len(slots)} slots")
                for slot in slots:
                    logger.info(f"      📅 {slot.date} - {slot.applicant_type}")
        else:
            logger.info(f"😔 No available slots found in any {navigation_type}")

        # Additional check: if we found no slots and reached max periods, log it
        if period_count >= max_periods:
            logger.warning(f"⚠️ Reached maximum {navigation_type} limit ({max_periods}). This might indicate an issue or no more dates available.")

        return all_available_slots

    async def check_all_weeks(self, page: Page) -> List[Dict]:
        """Check all available weeks for reservations."""
        return await self._check_periods(page, "week", max_periods=20)

    async def check_all_months(self, page: Page) -> List[Dict]:
        """Check all available months for reservations."""
        return await self._check_periods(page, "month", max_periods=20)

    async def is_end_of_available_dates(self, page: Page) -> bool:
        """Check if we've reached the end of available dates by examining page content."""
        try:
            # Check for common "no more dates" indicators
            no_dates_selectors = [
                'text="予約可能な日付がありません"',
                'text="No available dates"',
                'text="利用可能な日付がありません"',
                '.no-availability',
                '.no-dates'
            ]

            for selector in no_dates_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        logger.info(f"Found end-of-dates indicator: {selector}")
                        return True
                except:
                    continue

            # Check if the table is empty or has no facility rows
            facility_rows = await page.query_selector_all('tr')
            if len(facility_rows) <= 1:  # Only header row
                logger.info("Table appears to be empty - reached end of dates")
                return True

            return False

        except Exception as e:
            logger.warning(f"Error checking for end of dates: {e}")
            return False

    async def run_check(self, send_notifications=False, use_month_navigation=False, show_all=False):
        """Main method to run the reservation check."""
        logger.info("Starting reservation check...")

        # Log environment info for debugging
        import platform
        import os
        import time
        logger.info(f"🔧 Environment: Python {platform.python_version()}, OS: {platform.system()}")
        logger.info(f"🔧 Headless mode: {HEADLESS}, Timeout: {TIMEOUT}ms")

        try:
            async with async_playwright() as p:
                logger.info("🔧 Launching browser...")
                browser = await p.chromium.launch(headless=HEADLESS)
                logger.info("✅ Browser launched successfully")

                context = await browser.new_context()
                logger.info("✅ Browser context created")

                async def block_resource(route, request):
                    if request.resource_type in ["image", "stylesheet", "font"]:
                        await route.abort()
                    else:
                        await route.continue_()
                await context.route("**/*", block_resource)
                logger.info("✅ Resource blocking configured")

                page = await context.new_page()
                logger.info("✅ New page created")

                # Set user agent to avoid detection
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                })
                logger.info("✅ User agent set")

                logger.info(f"🔍 Navigating to: {self.target_url}")
                try:
                    start_time = time.time()
                    await page.goto(self.target_url, timeout=TIMEOUT)
                    nav_time = time.time() - start_time
                    logger.info(f"✅ Page navigation successful in {nav_time:.2f} seconds")

                    # Get page title and URL for debugging
                    title = await page.title()
                    current_url = page.url
                    logger.info(f"📄 Page title: {title}")
                    logger.info(f"🔗 Current URL: {current_url}")

                    # Check if we got redirected
                    if current_url != self.target_url:
                        logger.warning(f"⚠️ Redirected from {self.target_url} to {current_url}")

                except Exception as nav_error:
                    logger.error(f"❌ Navigation failed: {nav_error}")
                    raise

                if use_month_navigation:
                    available_slots = await self.check_all_months(page)
                else:
                    available_slots = await self.check_all_weeks(page)
                await browser.close()

                if available_slots:
                    check = CheckResult.from_slots(
                        available_slots,
                        target_url=self.target_url,
                        facilities_label=tuple(self.target_facilities),
                    )
                    if not show_all and SHOW_ONLY_RELEVANT_APPLICANTS and self.target_slot_types:
                        filtered = filter_slots(check.slots, keep_types=self.target_slot_types)
                        if not filtered:
                            return CheckResult.from_error(
                                f"❌ No relevant slots found (only showing {', '.join(self.target_slot_types)})",
                                target_url=self.target_url,
                                facilities_label=tuple(self.target_facilities),
                            )
                        logger.info(
                            f"🔍 Filtered results: {len(check.slots)} total slots → {len(filtered)} relevant slots"
                        )
                        check = CheckResult.from_slots(
                            filtered,
                            target_url=self.target_url,
                            facilities_label=tuple(self.target_facilities),
                        )

                    result_message = format_check_message(check)
                    if send_notifications:
                        if os.environ.get("ALLOW_STANDALONE_NOTIFY") == "1":
                            logger.warning(
                                "Sending via scraper send_telegram_message (bypasses run_bot filters). "
                                "Use only for deliberate debugging."
                            )
                            await self.send_telegram_message(result_message)
                        else:
                            logger.warning(
                                "send_notifications=True ignored. Run run_bot.py for production delivery, "
                                "or set ALLOW_STANDALONE_NOTIFY=1 to force legacy broadcast."
                            )
                    return check

                logger.info("No available slots found")
                return CheckResult.no_slots(
                    target_url=self.target_url,
                    facilities_label=tuple(self.target_facilities),
                )
        except Exception as e:
            error_msg = str(e)
            # Clean up error message to avoid HTML parsing issues
            if "Host system is missing dependencies" in error_msg:
                error_msg = "❌ Browser dependencies missing on server. Please contact administrator."
            elif "Can't parse entities" in error_msg:
                error_msg = "❌ Error processing response. Please try again."
            else:
                # Remove any HTML-like characters that might cause parsing issues
                error_msg = error_msg.replace("<", "&lt;").replace(">", "&gt;")
                error_msg = f"❌ Error during reservation check: {error_msg}"

            logger.error(f"Error during reservation check: {e}")
            return CheckResult.from_error(
                error_msg,
                target_url=self.target_url,
                facilities_label=tuple(self.target_facilities),
            )

    async def process_available_slots(
        self,
        slots: List,
        send_notifications=True,
        filter_applicants=None,
    ) -> str:
        """Format available slots for notification or user display (returns HTML string)."""
        if not slots:
            return ""

        if filter_applicants is None:
            filter_applicants = SHOW_ONLY_RELEVANT_APPLICANTS

        check = CheckResult.from_slots(
            slots,
            target_url=self.target_url,
            facilities_label=tuple(self.target_facilities),
        )
        apply_default = (
            list(self.target_slot_types) if filter_applicants and self.target_slot_types else None
        )
        if apply_default and check.has_slots:
            filtered = filter_slots(check.slots, keep_types=apply_default)
            if not filtered:
                return f"❌ No relevant slots found (only showing {', '.join(self.target_slot_types)})"
            logger.info(
                f"🔍 Filtered results: {len(check.slots)} total slots → {len(filtered)} relevant slots"
            )
            check = CheckResult.from_slots(
                filtered,
                target_url=self.target_url,
                facilities_label=tuple(self.target_facilities),
            )
        return format_check_message(check)

async def main():
    """CLI debug: scrape and print; never notifies subscribers."""
    from app_logging import configure_logging

    configure_logging()
    checker = ReservationChecker()
    check = await checker.run_check(send_notifications=False)
    from domain import format_check_message

    print(format_check_message(check))

if __name__ == "__main__":
    asyncio.run(main())
