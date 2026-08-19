"""Sanity checks for saved HTML fixtures."""

import re
from pathlib import Path

from bs4 import BeautifulSoup

from reservation_checker_playwright import ReservationChecker

FIXTURES = Path(__file__).parent / 'fixtures'
DATE_MD_PATTERN = re.compile(r'\d{1,2}/\d{1,2}')


def _parse_available_slots(html: str, target_facilities: list[str], target_slot_types: list[str] | None = None):
    """Mirror production scraper slot detection on static HTML."""
    soup = BeautifulSoup(html, 'html.parser')
    date_headers: list[str] = []
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) < 3:
            continue
        headers = []
        for cell in cells:
            text = ' '.join(cell.get_text(strip=True).split())
            if DATE_MD_PATTERN.search(text):
                headers.append(text)
        if len(headers) >= 3:
            date_headers = headers
            break

    available = []
    current_facility = None
    for row in soup.find_all('tr'):
        cells = row.find_all(['th', 'td'])
        if len(cells) < 2:
            continue
        first_text = cells[0].get_text(strip=True)
        second_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
        resolved = ReservationChecker._resolve_calendar_row(
            first_text, second_text, current_facility, target_facilities
        )
        if not resolved:
            continue
        current_facility, facility, applicant_type, date_start = resolved
        applicant_type = ReservationChecker._normalize_label(applicant_type)
        if target_slot_types and applicant_type not in target_slot_types:
            continue
        for i, cell in enumerate(cells[date_start:]):
            svg = cell.find('svg')
            if not svg or svg.get('aria-label') != '予約可能':
                continue
            date = date_headers[i] if i < len(date_headers) else f'Unknown date {i + 1}'
            available.append(
                {'date': date, 'facility': facility, 'applicant_type': applicant_type}
            )
    return available


def test_tokyo_calendar_fixture_exists_and_has_slot_marker():
    html = (FIXTURES / 'tokyo_calendar_sample.html').read_text(encoding='utf-8')
    assert '予約可能' in html
    assert '府中試験場' in html or '鮫洲試験場' in html


def test_kanagawa_calendar_fixture_exists_and_has_expected_markers():
    html = (FIXTURES / 'kanagawa_calendar_sample.html').read_text(encoding='utf-8')
    assert '外国免許四輪車' in html
    assert '普通車' in html
    assert 'time--table' in html or 'id="TBL"' in html
    assert 'aria-label="予約可能"' in html
    assert '08/14' in html
    assert '2026年' in html


def test_kanagawa_fixture_parser_finds_configured_slots():
    html = (FIXTURES / 'kanagawa_calendar_sample.html').read_text(encoding='utf-8')
    slots = _parse_available_slots(
        html,
        target_facilities=['外国免許四輪車'],
        target_slot_types=['普通車ＡＭ', '普通車ＰＭ'],
    )
    assert len(slots) == 3
    am = [s for s in slots if s['applicant_type'] == '普通車ＡＭ']
    pm = [s for s in slots if s['applicant_type'] == '普通車ＰＭ']
    assert len(am) == 1 and '08/14' in am[0]['date']
    assert len(pm) == 2
    assert {s['date'] for s in pm} == {'08/13(Thu)', '08/14(Fri)'}


def test_saitama_calendar_fixture_exists_and_has_expected_markers():
    html = (FIXTURES / 'saitama_calendar_sample.html').read_text(encoding='utf-8')
    assert '外免　書類審査' in html
    assert '【１】１回目（初めて）' in html
    assert 'aria-label="予約可能"' in html
    assert '08/26' in html
    assert '2026年' in html


def test_saitama_fixture_parser_finds_configured_slots():
    html = (FIXTURES / 'saitama_calendar_sample.html').read_text(encoding='utf-8')
    slots = _parse_available_slots(
        html,
        target_facilities=['外免　書類審査'],
        target_slot_types=['【１】１回目（初めて）', '【２】２回目以降', '【３】免除国等'],
    )
    assert len(slots) == 3
    by_type = {s['applicant_type']: s for s in slots}
    assert set(by_type) == {'【１】１回目（初めて）', '【２】２回目以降', '【３】免除国等'}
    assert '08/26' in by_type['【１】１回目（初めて）']['date']
    assert '08/27' in by_type['【２】２回目以降']['date']
    assert '08/27' in by_type['【３】免除国等']['date']
    assert all(s['facility'] == '外免　書類審査' for s in slots)
