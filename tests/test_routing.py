"""Regression tests for subscriber source routing and facility filtering."""

import pytest
from run_bot import SamezuBot


def make_bot():
    return SamezuBot()


FORMATTED_TOKYO_BOTH = (
    "🎉 <b>Available Reservation Slots Found!</b>\n\n"
    "📍 <b>Facilities:</b> 府中試験場, 鮫洲試験場\n\n"
    "<b>To book, click the <i>予約可能 (reservable)</i> or <i>選択中 (selected)</i> mark on your desired date on the calendar. Then proceed with the booking process.</b>\n\n"
    "📅 <b>06/05 (Thu)</b>\n"
    "   🏢 <b>鮫洲試験場</b>\n"
    "      • 住民票のある方\n"
    "   🏢 <b>府中試験場</b>\n"
    "      • 住民票のある方\n"
    "\n"
    "🔗 <a href='http://example.com'>Book Now</a>"
)


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


# --- _filter_result_by_facilities ---


def test_filter_facilities_samezu_removes_fuchu():
    bot = make_bot()
    result = bot._filter_result_by_facilities(FORMATTED_TOKYO_BOTH, ["鮫洲試験場"])
    assert "🏢 <b>鮫洲試験場</b>" in result
    assert "🏢 <b>府中試験場</b>" not in result
    assert "住民票のある方" in result


def test_filter_facilities_fuchu_removes_samezu():
    bot = make_bot()
    result = bot._filter_result_by_facilities(FORMATTED_TOKYO_BOTH, ["府中試験場"])
    assert "🏢 <b>府中試験場</b>" in result
    assert "🏢 <b>鮫洲試験場</b>" not in result


def test_filter_facilities_no_match_returns_no_slots():
    bot = make_bot()
    result = bot._filter_result_by_facilities(FORMATTED_TOKYO_BOTH, ["外国免許四輪車"])
    assert "❌" in result
    assert "🎉" not in result


# --- _send_notifications_to_subscribers (real routing, mocked Telegram) ---


def test_notification_messages_tokyo_reaches_samezu_subscriber():
    bot = make_bot()
    bot.get_subscribers = lambda: [("111", "@alice|samezu|relevant")]

    messages = bot._notification_messages_for_subscribers(FORMATTED_TOKYO_BOTH, source="tokyo")

    assert len(messages) == 1
    assert messages[0][0] == 111
    assert "🏢 <b>鮫洲試験場</b>" in messages[0][1]
    assert "🏢 <b>府中試験場</b>" not in messages[0][1]


def test_notification_messages_tokyo_skips_kanagawa_only_subscriber():
    bot = make_bot()
    bot.get_subscribers = lambda: [("222", "@bob|kanagawa|relevant")]

    messages = bot._notification_messages_for_subscribers(FORMATTED_TOKYO_BOTH, source="tokyo")

    assert messages == []


def test_notification_messages_kanagawa_reaches_kanagawa_subscriber():
    bot = make_bot()
    kanagawa_result = (
        "🎉 <b>Available Reservation Slots Found!</b>\n\n"
        "📅 <b>06/05 (Thu)</b>\n"
        "   🏢 <b>外国免許四輪車</b>\n"
        "      • 普通車ＡＭ\n"
        "\n"
        "🔗 <a href='http://example.com'>Book Now</a>"
    )
    bot.get_subscribers = lambda: [("333", "@carol|kanagawa|relevant")]

    messages = bot._notification_messages_for_subscribers(kanagawa_result, source="kanagawa")

    assert len(messages) == 1
    assert "普通車ＡＭ" in messages[0][1]


# --- _apply_check_filters for /check samezu ---


def test_filter_facilities_drops_empty_date_sections():
    bot = make_bot()
    both_dates = (
        "🎉 <b>Available Reservation Slots Found!</b>\n\n"
        "📍 <b>Facilities:</b> 府中試験場, 鮫洲試験場\n\n"
        "📅 <b>06/05 (Thu)</b>\n"
        "   🏢 <b>鮫洲試験場</b>\n"
        "      • 住民票のある方\n"
        "\n"
        "📅 <b>06/07 (Sat)</b>\n"
        "   🏢 <b>府中試験場</b>\n"
        "      • 住民票のある方\n"
        "\n"
        "🔗 <a href='http://example.com'>Book Now</a>"
    )
    result = bot._filter_result_by_facilities(both_dates, ["鮫洲試験場"])
    assert "📅 <b>06/05 (Thu)</b>" in result
    assert "📅 <b>06/07 (Sat)</b>" not in result
    assert "🏢 <b>府中試験場</b>" not in result


def test_apply_check_filters_samezu_on_cached_tokyo_result():
    bot = make_bot()
    result = bot._apply_check_filters(
        FORMATTED_TOKYO_BOTH,
        bot.reservation_checker,
        show_all=True,
        check_source="samezu",
    )
    assert "🏢 <b>鮫洲試験場</b>" in result
    assert "🏢 <b>府中試験場</b>" not in result
