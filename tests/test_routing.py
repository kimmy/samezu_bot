"""Regression tests for subscriber source routing and facility filtering."""

import pytest
from domain import format_check_message
from run_bot import SamezuBot
from tests.test_helpers import (
    CHECK_KANAGAWA,
    CHECK_TOKYO_BOTH,
    check_from_slots,
)


def make_bot():
    return SamezuBot()


# --- _subscriber_matches_source ---


def test_subscriber_matches_tokyo_when_samezu():
    bot = make_bot()
    assert bot._subscriber_matches_source(["samezu"], "tokyo")


def test_subscriber_matches_tokyo_when_fuchu():
    bot = make_bot()
    assert bot._subscriber_matches_source(["fuchu"], "tokyo")


def test_subscriber_matches_tokyo_when_both_tokyo_sources():
    bot = make_bot()
    assert bot._subscriber_matches_source(["samezu", "fuchu", "kanagawa"], "tokyo")


def test_subscriber_does_not_match_tokyo_when_kanagawa_only():
    bot = make_bot()
    assert not bot._subscriber_matches_source(["kanagawa"], "tokyo")


def test_subscriber_matches_kanagawa():
    bot = make_bot()
    assert bot._subscriber_matches_source(["kanagawa"], "kanagawa")


def test_subscriber_does_not_match_kanagawa_when_tokyo_only():
    bot = make_bot()
    assert not bot._subscriber_matches_source(["samezu", "fuchu"], "kanagawa")


# --- _facilities_for_subscriber_sources ---


def test_facilities_for_subscriber_samezu_only():
    bot = make_bot()
    assert bot._facilities_for_subscriber_sources(["samezu"]) == ["鮫洲試験場"]


def test_facilities_for_subscriber_both_tokyo_returns_none():
    bot = make_bot()
    assert bot._facilities_for_subscriber_sources(["samezu", "fuchu"]) is None


# --- facility filtering via format_check_message ---


def test_filter_facilities_samezu_removes_fuchu():
    bot = make_bot()
    result = format_check_message(CHECK_TOKYO_BOTH, keep_facilities=["鮫洲試験場"])
    assert "📍 <b>Facilities:</b> 鮫洲試験場" in result
    assert "府中試験場" not in result.split("To book")[0]
    assert "🏢 <b>鮫洲試験場</b>" in result
    assert "🏢 <b>府中試験場</b>" not in result
    assert "住民票のある方" in result


def test_filter_facilities_fuchu_removes_samezu():
    bot = make_bot()
    result = format_check_message(CHECK_TOKYO_BOTH, keep_facilities=["府中試験場"])
    assert "📍 <b>Facilities:</b> 府中試験場" in result
    assert "鮫洲試験場" not in result.split("To book")[0]
    assert "🏢 <b>府中試験場</b>" in result
    assert "🏢 <b>鮫洲試験場</b>" not in result


def test_filter_facilities_no_orphan_header_without_bullets():
    """Facility with no slot lines must not appear after filtering."""
    bot = make_bot()
    check = check_from_slots(
        [{"date": "06/05 (Thu)", "facility": "府中試験場", "applicant_type": "住民票のある方"}],
        facilities_label=["府中試験場", "鮫洲試験場"],
    )
    result = format_check_message(check, keep_facilities=["鮫洲試験場"])
    assert "❌" in result
    assert "🏢 <b>鮫洲試験場</b>" not in result


def test_filter_facilities_no_match_returns_no_slots():
    bot = make_bot()
    result = format_check_message(CHECK_TOKYO_BOTH, keep_facilities=["外国免許四輪車"])
    assert "❌" in result
    assert "🎉" not in result


# --- _send_notifications_to_subscribers (real routing, mocked Telegram) ---


def test_notification_messages_tokyo_reaches_samezu_subscriber():
    bot = make_bot()
    bot.get_subscribers = lambda: [("111", "@alice|samezu|relevant")]

    messages = bot._notification_messages_for_subscribers(CHECK_TOKYO_BOTH, source="tokyo")

    assert len(messages) == 1
    assert messages[0][0] == 111
    assert "📍 <b>Facilities:</b> 鮫洲試験場" in messages[0][1]
    assert "府中試験場" not in messages[0][1].split("To book")[0]
    assert "🏢 <b>鮫洲試験場</b>" in messages[0][1]
    assert "🏢 <b>府中試験場</b>" not in messages[0][1]


def test_notification_messages_tokyo_skips_kanagawa_only_subscriber():
    bot = make_bot()
    bot.get_subscribers = lambda: [("222", "@bob|kanagawa|relevant")]

    messages = bot._notification_messages_for_subscribers(CHECK_TOKYO_BOTH, source="tokyo")

    assert messages == []


def test_notification_messages_kanagawa_reaches_kanagawa_subscriber():
    bot = make_bot()
    bot.get_subscribers = lambda: [("333", "@carol|kanagawa|relevant")]

    messages = bot._notification_messages_for_subscribers(CHECK_KANAGAWA, source="kanagawa")

    assert len(messages) == 1
    assert "普通車ＡＭ" in messages[0][1]


# --- _apply_check_filters for /check samezu ---


def test_filter_facilities_drops_empty_date_sections():
    bot = make_bot()
    both_dates = check_from_slots(
        [
            {"date": "06/05 (Thu)", "facility": "鮫洲試験場", "applicant_type": "住民票のある方"},
            {"date": "06/07 (Sat)", "facility": "府中試験場", "applicant_type": "住民票のある方"},
        ],
        facilities_label=["府中試験場", "鮫洲試験場"],
    )
    result = format_check_message(both_dates, keep_facilities=["鮫洲試験場"])
    assert "📅 <b>06/05 (Thu)</b>" in result
    assert "📅 <b>06/07 (Sat)</b>" not in result
    assert "🏢 <b>府中試験場</b>" not in result


def test_apply_check_filters_samezu_on_cached_tokyo_result():
    bot = make_bot()
    result = bot._format_check_for_user(
        CHECK_TOKYO_BOTH,
        bot.reservation_checker,
        show_all=True,
        check_source="samezu",
    )
    assert "🏢 <b>鮫洲試験場</b>" in result
    assert "🏢 <b>府中試験場</b>" not in result
