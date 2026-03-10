#!/usr/bin/env python3
"""
Tokyo Police Department Reservation Checker
Checks for available reservation slots using requests + BeautifulSoup.
Lightweight alternative to the Playwright version - no browser required.
"""

import logging
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from telegram import Bot

from config_template import *

try:
    import config
    for var in dir(config):
        if not var.startswith('_') and var.isupper():
            globals()[var] = getattr(config, var)
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reservation_checker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BASE_URL = "https://www.keishicho-gto.metro.tokyo.lg.jp"
NAV_URL_TEMPLATE = BASE_URL + "/keishicho-u/reserve/facilitySelect_dateTrans?movePage={move}"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'ja,en;q=0.9',
}


class ReservationChecker:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.available_slots = []

    def _make_session(self):
        session = requests.Session()
        session.headers.update(HEADERS)
        return session

    def _get_form_data(self, soup):
        """Extract hidden form fields needed for navigation."""
        form = soup.find('form')
        if not form:
            return {}
        return {
            inp.get('name'): inp.get('value', '')
            for inp in form.find_all('input')
            if inp.get('name')
        }

    def _get_dates(self, soup) -> List[str]:
        """Extract date headers from the second table row."""
        rows = soup.find_all('tr')
        if len(rows) > 1:
            return [
                td.get_text(strip=True)
                for td in rows[1].find_all('td')
                if td.get_text(strip=True)
            ]
        return []

    def _is_end_of_dates(self, soup, nav_button_value) -> bool:
        """Check if the next navigation button is absent or disabled."""
        btn = soup.find('input', {'value': nav_button_value})
        if not btn:
            return True
        # Button is disabled if it has a disabled attribute or aria-disabled
        if btn.get('disabled') or btn.get('aria-disabled') == 'true':
            return True
        return False

    def _get_available_slots(self, soup, date_headers: List[str]) -> List[Dict]:
        """Extract available slots from the current page."""
        available = []
        rows = soup.find_all('tr')

        for row in rows:
            facility_cell = row.find(['th', 'td'])
            if not facility_cell:
                continue

            facility_text = facility_cell.get_text(strip=True)
            target_facility = next(
                (f for f in TARGET_FACILITIES if f in facility_text), None
            )
            if not target_facility:
                continue

            # Get applicant type from second cell
            cells = row.find_all(['th', 'td'])
            if len(cells) < 2:
                continue
            applicant_type = cells[1].get_text(strip=True)

            # Check date cells (skip first two: facility name + applicant type)
            date_cells = row.find_all('td')
            # Filter out the first cells that are facility/applicant info
            slot_cells = [
                td for td in date_cells
                if not any(f in td.get_text() for f in TARGET_FACILITIES)
                and applicant_type not in td.get_text()
            ]

            for i, cell in enumerate(slot_cells):
                svg = cell.find('svg')
                if not svg:
                    continue
                aria_label = svg.get('aria-label', '')
                if aria_label == '予約可能':
                    date = date_headers[i] if i < len(date_headers) else f'Unknown date {i+1}'
                    available.append({
                        'date': date,
                        'facility': target_facility,
                        'applicant_type': applicant_type,
                    })
                    logger.info(f"✅ Found slot: {date} - {target_facility} - {applicant_type}")
                elif aria_label == '空き無':
                    logger.debug(f"❌ No availability: {date_headers[i] if i < len(date_headers) else i} - {applicant_type}")

        return available

    async def _check_periods(self, session, move_param: str, nav_button_value: str, max_periods: int = 20) -> List[Dict]:
        """Navigate through all available periods and collect slots."""
        all_slots = []

        # Load initial page
        resp = session.get(TARGET_URL, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        title = soup.title.string.strip() if soup.title else ''
        if 'Waiting Room' in title:
            raise Exception("Cloudflare waiting room active — try again in a few minutes")

        logger.info(f"✅ Page loaded: {title}")
        form_data = self._get_form_data(soup)

        last_dates = None
        for period in range(1, max_periods + 1):
            logger.info(f"🔄 Checking period {period}")

            date_headers = self._get_dates(soup)
            if date_headers:
                logger.info(f"📅 Dates: {date_headers[0]} to {date_headers[-1]}")

            # Stop if dates haven't changed (server returned same page = end of calendar)
            if date_headers and date_headers == last_dates:
                logger.info("🏁 Dates unchanged — reached end of available dates")
                break
            last_dates = date_headers

            slots = self._get_available_slots(soup, date_headers)
            all_slots.extend(slots)

            if slots:
                logger.info(f"🎯 Period {period}: Found {len(slots)} slots")
            else:
                logger.info(f"📭 Period {period}: No slots")

            if self._is_end_of_dates(soup, nav_button_value):
                logger.info("🏁 Reached end of available dates")
                break

            # Navigate to next period
            nav_url = NAV_URL_TEMPLATE.format(move=move_param)
            resp = session.post(nav_url, data=form_data, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            form_data = self._get_form_data(soup)

        logger.info(f"📊 SUMMARY: Checked {period} periods, found {len(all_slots)} total slots")
        return all_slots

    async def send_telegram_message(self, message: str):
        """Send message to all subscribed users."""
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
                tagged_message = f"🔔 {user_info}\n\n{message}" if user_info else message
                await self.bot.send_message(
                    chat_id=int(chat_id),
                    text=tagged_message,
                    parse_mode='HTML'
                )
                logger.info(f"Message sent to {chat_id}")
            except Exception as e:
                logger.error(f"Failed to send to {chat_id}: {e}")

    async def run_check(self, send_notifications=True, use_month_navigation=False, show_all=False):
        """Main method to run the reservation check."""
        logger.info("Starting reservation check...")

        try:
            session = self._make_session()

            if use_month_navigation:
                slots = await self._check_periods(
                    session,
                    move_param='nextMonth',
                    nav_button_value='1か月後＞',
                )
            else:
                slots = await self._check_periods(
                    session,
                    move_param='next',
                    nav_button_value='2週後＞',
                )

            if slots:
                filter_applicants = not show_all
                result = await self.process_available_slots(slots, send_notifications, filter_applicants=filter_applicants)
                if send_notifications:
                    await self.send_telegram_message(result)
                return result
            else:
                logger.info("No available slots found")
                return "❌ No slots"

        except Exception as e:
            error_msg = str(e).replace("<", "&lt;").replace(">", "&gt;")
            error_msg = f"❌ Error during reservation check: {error_msg}"
            logger.error(f"Error during reservation check: {e}")
            return error_msg

    async def process_available_slots(self, slots: List[Dict], send_notifications=True, filter_applicants=None):
        """Format available slots for display."""
        if not slots:
            return ""

        if filter_applicants is None:
            filter_applicants = SHOW_ONLY_RELEVANT_APPLICANTS

        if filter_applicants:
            original_count = len(slots)
            slots = [s for s in slots if "住民票のある方" in s['applicant_type']]
            if not slots:
                return "❌ No relevant slots found (only showing 住民票のある方)"
            logger.info(f"🔍 Filtered: {original_count} total → {len(slots)} relevant slots")

        slots_by_date_facility = {}
        for slot in slots:
            date, facility, applicant_type = slot['date'], slot['facility'], slot['applicant_type']
            slots_by_date_facility.setdefault(date, {}).setdefault(facility, []).append(applicant_type)

        message = "🎉 <b>Available Reservation Slots Found!</b>\n\n"
        message += f"📍 <b>Facilities:</b> {', '.join(TARGET_FACILITIES)}\n\n"
        message += "<b>To book, click the <i>予約可能 (reservable)</i> or <i>選択中 (selected)</i> mark on your desired date on the calendar. Then proceed with the booking process.</b>\n\n"

        for date, facilities in slots_by_date_facility.items():
            message += f"📅 <b>{date}</b>\n"
            for facility, applicant_types in facilities.items():
                message += f"   🏢 <b>{facility}</b>\n"
                for applicant_type in applicant_types:
                    message += f"      • {applicant_type} — <a href='{TARGET_URL}'>Book</a>\n"
            message += "\n"

        message += f"🔗 <a href='{TARGET_URL}'>Book Now</a>"
        return message


async def main():
    checker = ReservationChecker()
    await checker.run_check()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
