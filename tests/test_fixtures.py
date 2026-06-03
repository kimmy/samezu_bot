"""Sanity checks for saved HTML fixtures."""

from pathlib import Path

FIXTURES = Path(__file__).parent / 'fixtures'


def test_tokyo_calendar_fixture_exists_and_has_slot_marker():
    html = (FIXTURES / 'tokyo_calendar_sample.html').read_text(encoding='utf-8')
    assert '予約可能' in html
    assert '府中試験場' in html or '鮫洲試験場' in html


def test_kanagawa_calendar_fixture_exists_and_has_expected_markers():
    html = (FIXTURES / 'kanagawa_calendar_sample.html').read_text(encoding='utf-8')
    assert '外国免許四輪車' in html
    assert '普通車' in html
    assert 'time--table' in html or 'id="TBL"' in html
