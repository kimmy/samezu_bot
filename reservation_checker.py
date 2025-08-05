#!/usr/bin/env python3
"""
Tokyo Police Department Reservation Checker
Automatically checks for available reservation slots at 鮫洲試験場
and sends Telegram notifications when slots are found.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Tuple
from playwright.async_api import async_playwright, Page
from telegram import Bot
# Try to import from config first (for local), fallback to config_template (for Railway)
try:
    from config import (
        TELEGRAM_BOT_TOKEN,
        TARGET_URL,
        TARGET_FACILITIES,
        HEADLESS,
        TIMEOUT
    )
except ImportError:
    from config_template import (
        TELEGRAM_BOT_TOKEN,
        TARGET_URL,
        TARGET_FACILITIES,
        HEADLESS,
        TIMEOUT
    )

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reservation_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ReservationChecker:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.available_slots = []

    async def send_telegram_message(self, message: str):
        """Send message to all subscribed users (only for slot notifications)."""
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
        """Wait for the page to load completely."""
        try:
            # Wait for the table to be present
            await page.wait_for_selector('table', timeout=TIMEOUT)

            # Wait for any loading indicators to disappear
            try:
                await page.wait_for_selector('.loading, .spinner, [aria-busy="true"]',
                                          state='hidden', timeout=5000)
            except:
                pass  # No loading indicators found, that's fine

            # Wait a bit more for dynamic content
            await page.wait_for_timeout(2000)

            # Verify the page has loaded by checking for facility names
            facility_elements = await page.query_selector_all('td')
            if not facility_elements:
                raise Exception("No table data found on page")

        except Exception as e:
            logger.error(f"Timeout waiting for page load: {e}")
            raise

    async def get_available_dates(self, page: Page) -> List[Dict]:
        """Extract available dates from the current page."""
        available_slots = []

        try:
            # Get date information from the second row (which contains the actual dates)
            rows = await page.query_selector_all('tr')
            week_dates = []

            if len(rows) > 1:
                # Get the second row (index 1) which contains the dates
                date_row = rows[1]
                date_cells = await date_row.query_selector_all('td')

                for cell in date_cells:
                    date_text = await cell.text_content()
                    if date_text and date_text.strip():
                        # Clean up the date text (remove extra whitespace and newlines)
                        clean_date = ' '.join(date_text.strip().split())
                        if clean_date and len(clean_date) > 2:  # Filter out empty or very short text
                            week_dates.append(clean_date)

            # Log the week range
            if week_dates:
                start_date = week_dates[0] if len(week_dates) > 0 else "Unknown"
                end_date = week_dates[-1] if len(week_dates) > 0 else "Unknown"
                logger.info(f"📅 Checking dates: {start_date} to {end_date}")
            else:
                logger.info("📅 Date range: Unable to determine")

            # Find all rows for target facilities
            rows = await page.query_selector_all('tr')

            for row in rows:
                # Get the facility name from the first cell
                facility_cell = await row.query_selector('td:first-child')
                if not facility_cell:
                    continue

                facility_text = await facility_cell.text_content()
                if not facility_text:
                    continue

                # Check if this row is for any of our target facilities
                target_facility = None
                for facility in TARGET_FACILITIES:
                    if facility in facility_text:
                        target_facility = facility
                        break

                if not target_facility:
                    continue

                # Get applicant type from second cell
                applicant_cell = await row.query_selector('td:nth-child(2)')
                if not applicant_cell:
                    continue

                applicant_type = await applicant_cell.text_content()
                applicant_type = applicant_type.strip() if applicant_type else "Unknown"

                # Check all date cells for availability
                date_cells = await row.query_selector_all('td:not(:first-child):not(:nth-child(2))')

                for i, cell in enumerate(date_cells):
                    # Get the date from the header
                    date_header = await page.query_selector(f'th:nth-child({i + 3})')
                    if not date_header:
                        continue

                    date_text = await date_header.text_content()
                    date_text = date_text.strip() if date_text else ""

                    # Check for available slot
                    svg = await cell.query_selector('svg')
                    if svg:
                        aria_label = await svg.get_attribute('aria-label')
                        if aria_label == "予約可能":
                            available_slots.append({
                                'date': date_text,
                                'facility': target_facility,
                                'applicant_type': applicant_type
                            })
                            logger.info(f"✅ Found available slot: {date_text} - {target_facility} - {applicant_type}")
                        elif aria_label == "空き無":
                            logger.debug(f"❌ No availability: {date_text} - {applicant_type}")
                        elif aria_label == "時間外":
                            logger.debug(f"⏰ Outside hours: {date_text} - {applicant_type}")

        except Exception as e:
            logger.error(f"Error extracting available dates: {e}")

        return available_slots

    async def check_all_weeks(self, page: Page) -> List[Dict]:
        """Check all available weeks for reservations."""
        all_available_slots = []
        week_count = 0
        max_weeks = 20  # Safety limit to prevent infinite loops

        while week_count < max_weeks:
            week_count += 1
            logger.info(f"🔄 Checking week {week_count}")

            # Wait for page to load
            await self.wait_for_page_load(page)

            # Check if we've reached the end of available dates
            if await self.is_end_of_available_dates(page):
                logger.info("🏁 Detected end of available dates")
                break

            # Get available slots from current page
            current_slots = await self.get_available_dates(page)
            all_available_slots.extend(current_slots)

            # Log summary for this week
            if current_slots:
                logger.info(f"🎯 Week {week_count}: Found {len(current_slots)} available slots")
            else:
                logger.info(f"📭 Week {week_count}: No available slots found")

            # Check for "Next 2 Weeks" button with better detection
            try:
                # Look for the next button with multiple selectors
                next_button = await page.query_selector('input[value="2週後＞"]')

                if not next_button:
                    logger.info("Next button not found - reached end of available dates")
                    break

                # Check if button is disabled or has no-click attribute
                is_disabled = await next_button.get_attribute('disabled')
                is_clickable = await next_button.is_enabled()
                aria_label = await next_button.get_attribute('aria-label')

                # Log button status for debugging
                logger.info(f"🔘 Next button status - disabled: {is_disabled}, enabled: {is_clickable}, aria-label: {aria_label}")

                # If button is disabled or not clickable, we've reached the end
                if is_disabled or not is_clickable:
                    logger.info("Next button is disabled/not clickable - reached end of available dates")
                    break

                # Try to click the button
                await next_button.click()
                logger.info("✅ Successfully clicked next button")

                # Wait for page transition with better error handling
                try:
                    await page.wait_for_timeout(3000)  # Increased wait time
                    # Additional check to ensure page loaded
                    await page.wait_for_selector('table', timeout=10000)
                except Exception as e:
                    logger.warning(f"Page transition timeout: {e}")
                    # Continue anyway as the page might have loaded

            except Exception as e:
                logger.info(f"Error with next button or reached end: {e}")
                break

        # Final summary
        logger.info(f"📊 SUMMARY: Checked {week_count} weeks, found {len(all_available_slots)} total available slots")

        if all_available_slots:
            # Show details of found slots grouped by facility
            logger.info("🎉 Available slots found:")
            slots_by_facility = {}
            for slot in all_available_slots:
                facility = slot['facility']
                if facility not in slots_by_facility:
                    slots_by_facility[facility] = []
                slots_by_facility[facility].append(slot)

            for facility, slots in slots_by_facility.items():
                logger.info(f"   🏢 {facility}: {len(slots)} slots")
                for slot in slots:
                    logger.info(f"      📅 {slot['date']} - {slot['applicant_type']}")
        else:
            logger.info("😔 No available slots found in any week")

        # Additional check: if we found no slots and reached max weeks, log it
        if week_count >= max_weeks:
            logger.warning(f"⚠️ Reached maximum week limit ({max_weeks}). This might indicate an issue or no more dates available.")

        return all_available_slots

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

    async def run_check(self, send_notifications=True):
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

                logger.info(f"🔍 Navigating to: {TARGET_URL}")
                try:
                    start_time = time.time()
                    await page.goto(TARGET_URL, timeout=TIMEOUT)
                    nav_time = time.time() - start_time
                    logger.info(f"✅ Page navigation successful in {nav_time:.2f} seconds")

                    # Get page title and URL for debugging
                    title = await page.title()
                    current_url = page.url
                    logger.info(f"📄 Page title: {title}")
                    logger.info(f"🔗 Current URL: {current_url}")

                    # Check if we got redirected
                    if current_url != TARGET_URL:
                        logger.warning(f"⚠️ Redirected from {TARGET_URL} to {current_url}")

                except Exception as nav_error:
                    logger.error(f"❌ Navigation failed: {nav_error}")
                    raise

                available_slots = await self.check_all_weeks(page)
                await browser.close()

                if available_slots:
                    result_message = await self.process_available_slots(available_slots, send_notifications)
                    # Only notify subscribers if this is a scheduled/cron run
                    if send_notifications:
                        await self.send_telegram_message(result_message)
                    return result_message
                else:
                    logger.info("No available slots found")
                    return "❌ No slots"
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
            return error_msg

    async def process_available_slots(self, slots: List[Dict], send_notifications=True):
        """Format available slots for notification or user display."""
        if not slots:
            return ""

        slots_by_date_facility = {}
        for slot in slots:
            date = slot['date']
            facility = slot['facility']
            applicant_type = slot['applicant_type']
            link = slot.get('link', TARGET_URL)
            if date not in slots_by_date_facility:
                slots_by_date_facility[date] = {}
            if facility not in slots_by_date_facility[date]:
                slots_by_date_facility[date][facility] = []
            slots_by_date_facility[date][facility].append({
                'applicant_type': applicant_type,
                'link': link
            })

        # Create message
        message = "🎉 <b>Available Reservation Slots Found!</b>\n\n"
        message += f"📍 <b>Facilities:</b> {', '.join(TARGET_FACILITIES)}\n\n"
        message += "<b>To book, click the <i>予約可能 (reservable)</i> or <i>選択中 (selected)</i> mark on your desired date on the calendar. Then proceed with the booking process.</b>\n\n"

        for date, facilities in slots_by_date_facility.items():
            message += f"📅 <b>{date}</b>\n"
            for facility, slot_details in facilities.items():
                message += f"   🏢 <b>{facility}</b>\n"
                for detail in slot_details:
                    applicant_type = detail['applicant_type']
                    link = detail['link']
                    message += f"      • {applicant_type} — <a href='{link}'>Book</a>\n"
            message += "\n"

        if not any(slot.get('link') for slot in slots):
            message += f"🔗 <a href='{TARGET_URL}'>Book Now</a>"

        return message

async def main():
    """Main entry point."""
    checker = ReservationChecker()
    await checker.run_check()

if __name__ == "__main__":
    asyncio.run(main())
