import pytest
from domain import NO_SLOTS_MESSAGE, format_check_message
from run_bot import SamezuBot
from tests.test_helpers import (
    CHECK_KANAGAWA,
    CHECK_NO_SLOTS,
    CHECK_SAITAMA_MIXED,
    CHECK_TOKYO_MIXED,
    CHECK_TOKYO_SPLIT,
    KANAGAWA_SLOTS,
    SAITAMA_MIXED_SLOTS,
    check_error,
    check_from_slots,
)


# --- Fixtures ---

def make_bot():
    return SamezuBot()


TOKYO_SLOTS_MIXED = [
    {'date': '06/05 (Thu)', 'facility': '鮫洲試験場', 'applicant_type': '住民票のある方'},
    {'date': '06/05 (Thu)', 'facility': '鮫洲試験場', 'applicant_type': '住民票のない方'},
    {'date': '06/07 (Sat)', 'facility': '府中試験場', 'applicant_type': '住民票のある方'},
]

TOKYO_SLOTS_ARI_ONLY = [
    {'date': '06/05 (Thu)', 'facility': '鮫洲試験場', 'applicant_type': '住民票のある方'},
]

TOKYO_SLOTS_NAI_ONLY = [
    {'date': '06/05 (Thu)', 'facility': '鮫洲試験場', 'applicant_type': '住民票のない方'},
]

TOKYO_LONG_NAI_SLOT = {
    'date': '08/21 (Thu)',
    'facility': '鮫洲試験場',
    'applicant_type': '29の国･地域以外の方で、住民票のない方',
}


# --- process_available_slots ---

@pytest.mark.asyncio
async def test_process_slots_contains_date_and_facility():
    bot = make_bot()
    result = await bot.reservation_checker.process_available_slots(TOKYO_SLOTS_MIXED, send_notifications=False, filter_applicants=False)
    assert '06/05 (Thu)' in result
    assert '鮫洲試験場' in result


@pytest.mark.asyncio
async def test_process_slots_contains_all_types_when_unfiltered():
    bot = make_bot()
    result = await bot.reservation_checker.process_available_slots(TOKYO_SLOTS_MIXED, send_notifications=False, filter_applicants=False)
    assert '住民票のある方' in result
    assert '住民票のない方' in result


@pytest.mark.asyncio
async def test_process_slots_filters_to_ari_only():
    bot = make_bot()
    result = await bot.reservation_checker.process_available_slots(TOKYO_SLOTS_MIXED, send_notifications=False, filter_applicants=True)
    assert '住民票のある方' in result
    assert '住民票のない方' not in result


@pytest.mark.asyncio
async def test_process_slots_exact_type_match_not_substring():
    """住民票のない方 must not match the 住民票のある方 filter."""
    bot = make_bot()
    result = await bot.reservation_checker.process_available_slots(
        TOKYO_SLOTS_NAI_ONLY, send_notifications=False, filter_applicants=True
    )
    assert '❌' in result


@pytest.mark.asyncio
async def test_process_slots_html_escapes_special_characters():
    bot = make_bot()
    slots = [
        {
            'date': '06/05 <test>',
            'facility': '鮫洲 & 試験場',
            'applicant_type': '住民票のある方',
        }
    ]
    result = await bot.reservation_checker.process_available_slots(
        slots, send_notifications=False, filter_applicants=False
    )
    assert '&amp;' in result
    assert '<test>' not in result


@pytest.mark.asyncio
async def test_process_slots_returns_no_slots_when_filtered_out():
    bot = make_bot()
    result = await bot.reservation_checker.process_available_slots(TOKYO_SLOTS_NAI_ONLY, send_notifications=False, filter_applicants=True)
    assert '❌' in result
    assert '🎉' not in result


@pytest.mark.asyncio
async def test_process_slots_empty_input_returns_empty():
    bot = make_bot()
    result = await bot.reservation_checker.process_available_slots([], send_notifications=False, filter_applicants=False)
    assert result == ""


@pytest.mark.asyncio
async def test_process_slots_multiple_dates_all_present():
    bot = make_bot()
    result = await bot.reservation_checker.process_available_slots(TOKYO_SLOTS_MIXED, send_notifications=False, filter_applicants=False)
    assert '06/05 (Thu)' in result
    assert '06/07 (Sat)' in result


# --- _filter_result_for_subscription ---


@pytest.mark.asyncio
async def test_filter_subscription_all_returns_both_types():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(CHECK_TOKYO_MIXED, "all", source="tokyo")
    assert '住民票のある方' in result
    assert '住民票のない方' in result


@pytest.mark.asyncio
async def test_filter_subscription_ari_keeps_ari_removes_nai():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(CHECK_TOKYO_MIXED, "ari", source="tokyo")
    assert '住民票のある方' in result
    assert '住民票のない方' not in result


@pytest.mark.asyncio
async def test_filter_subscription_nai_keeps_nai_removes_ari():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(CHECK_TOKYO_MIXED, "nai", source="tokyo")
    assert '住民票のない方' in result
    assert '住民票のある方' not in result


@pytest.mark.asyncio
async def test_filter_subscription_nai_matches_tokyo_long_form_scraped_label():
    bot = make_bot()
    check = check_from_slots([TOKYO_LONG_NAI_SLOT], facilities_label=["鮫洲試験場"])
    result = await bot._filter_result_for_subscription(check, "nai", source="tokyo")
    assert "08/21" in result
    assert TOKYO_LONG_NAI_SLOT["applicant_type"] in result
    assert "❌ No slots found" not in result


@pytest.mark.asyncio
async def test_filter_subscription_relevant_same_as_ari():
    bot = make_bot()
    ari = await bot._filter_result_for_subscription(CHECK_TOKYO_MIXED, "ari", source="tokyo")
    relevant = await bot._filter_result_for_subscription(CHECK_TOKYO_MIXED, "relevant", source="tokyo")
    assert ari == relevant


@pytest.mark.asyncio
async def test_filter_subscription_passes_through_no_slots():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(CHECK_NO_SLOTS, "ari", source="tokyo")
    assert result == NO_SLOTS_MESSAGE


@pytest.mark.asyncio
async def test_filter_subscription_passes_through_error():
    bot = make_bot()
    error = check_error("❌ Error during reservation check: timeout")
    result = await bot._filter_result_for_subscription(error, "all", source="tokyo")
    assert result == error.error


@pytest.mark.asyncio
async def test_filter_subscription_saitama_1_keeps_first_removes_others():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(CHECK_SAITAMA_MIXED, "1", source="saitama")
    assert '【１】１回目（初めて）' in result
    assert '【２】２回目以降' not in result
    assert '【３】免除国等' not in result


@pytest.mark.asyncio
async def test_filter_subscription_saitama_2_keeps_repeat_only():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(CHECK_SAITAMA_MIXED, "2", source="saitama")
    assert '【２】２回目以降' in result
    assert '【１】１回目（初めて）' not in result


@pytest.mark.asyncio
async def test_filter_subscription_saitama_relevant_same_as_1():
    bot = make_bot()
    first = await bot._filter_result_for_subscription(CHECK_SAITAMA_MIXED, "1", source="saitama")
    relevant = await bot._filter_result_for_subscription(CHECK_SAITAMA_MIXED, "relevant", source="saitama")
    assert first == relevant


def test_filter_slot_types_two_facilities_drops_orphan_samezu_header():
    """ARI filter must not leave 鮫洲 when only 府中 has matching bullets."""
    bot = make_bot()
    result = format_check_message(
        CHECK_TOKYO_SPLIT,
        keep_types=["住民票のある方"],
    )
    assert "📍 <b>Facilities:</b> 府中試験場" in result
    assert "鮫洲試験場" not in result.split("To book")[0]
    assert "🏢 <b>府中試験場</b>" in result
    assert "住民票のある方" in result
    assert "📅 <b>06/05 (Thu)</b>" in result
    assert "🏢 <b>鮫洲試験場</b>" not in result
    assert "住民票のない方" not in result


def test_apply_check_filters_samezu_no_false_positive_when_only_fuchu_has_ari():
    bot = make_bot()
    result = bot._format_check_for_user(
        CHECK_TOKYO_SPLIT,
        bot.reservation_checker,
        show_all=False,
        check_source="samezu",
    )
    assert "❌" in result
    assert "🎉" not in result
    assert "🏢 <b>鮫洲試験場</b>" not in result


# --- Subscriber round-trip ---

def test_add_and_get_subscriber(tmp_path, monkeypatch):
    bot = make_bot()
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(tmp_path / 'subscribers.txt'))
    bot.add_subscriber(99999, "@alice|relevant")
    subs = bot.get_subscribers()
    assert any(s[0] == '99999' for s in subs)


def test_upsert_subscriber_replaces_existing_line(tmp_path, monkeypatch):
    bot = make_bot()
    sub_file = tmp_path / 'subscribers.txt'
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(sub_file))
    bot.upsert_subscriber(99999, "@alice|samezu|relevant")
    bot.upsert_subscriber(99999, "@alice|kanagawa|am")
    subs = bot.get_subscribers()
    assert len(subs) == 1
    assert subs[0] == ('99999', '@alice|kanagawa|am')


def test_upsert_subscriber_removes_duplicate_chat_ids(tmp_path, monkeypatch):
    bot = make_bot()
    sub_file = tmp_path / 'subscribers.txt'
    sub_file.write_text("99999|old|relevant\n99999|older|all\n")
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(sub_file))
    bot.upsert_subscriber(99999, "@alice|fuchu|ari")
    subs = bot.get_subscribers()
    assert len(subs) == 1
    assert subs[0][1] == '@alice|fuchu|ari'


def test_remove_subscriber(tmp_path, monkeypatch):
    bot = make_bot()
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(tmp_path / 'subscribers.txt'))
    bot.add_subscriber(99999, "@alice|relevant")
    bot.remove_subscriber(99999)
    subs = bot.get_subscribers()
    assert not any(s[0] == '99999' for s in subs)


def test_get_subscribers_parses_pipe_format(tmp_path, monkeypatch):
    bot = make_bot()
    sub_file = tmp_path / 'subscribers.txt'
    sub_file.write_text("12345|@alice|relevant\n67890|@bob|all\n")
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(sub_file))
    subs = bot.get_subscribers()
    assert subs[0] == ('12345', '@alice|relevant')
    assert subs[1] == ('67890', '@bob|all')


def test_get_subscribers_handles_no_pipe(tmp_path, monkeypatch):
    bot = make_bot()
    sub_file = tmp_path / 'subscribers.txt'
    sub_file.write_text("12345\n")
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(sub_file))
    subs = bot.get_subscribers()
    assert subs[0] == ('12345', None)


def test_get_subscribers_empty_file(tmp_path, monkeypatch):
    bot = make_bot()
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(tmp_path / 'subscribers.txt'))
    subs = bot.get_subscribers()
    assert subs == []


# --- parse_subscriber_info ---

def test_parse_subscriber_info_new_format():
    bot = make_bot()
    username, sources, sub_type = bot.parse_subscriber_info("@alice|samezu,kanagawa|all")
    assert username == "@alice"
    assert sources == ["samezu", "kanagawa"]
    assert sub_type == "all"


def test_parse_subscriber_info_old_two_part_defaults_all_sources():
    bot = make_bot()
    username, sources, sub_type = bot.parse_subscriber_info("@alice|relevant")
    assert username == "@alice"
    assert set(sources) == {"samezu", "fuchu", "kanagawa"}
    assert sub_type == "relevant"


def test_parse_subscriber_info_none_defaults_all():
    bot = make_bot()
    username, sources, sub_type = bot.parse_subscriber_info(None)
    assert username is None
    assert set(sources) == {"samezu", "fuchu", "kanagawa"}
    assert sub_type == "relevant"


def test_parse_subscriber_info_kanagawa_only():
    bot = make_bot()
    username, sources, sub_type = bot.parse_subscriber_info("@bob|kanagawa|relevant")
    assert sources == ["kanagawa"]


# --- Kanagawa slot filtering ---

KANAGAWA_SLOTS_MIXED = [
    {'date': '06/05 (Thu)', 'facility': '外国免許四輪車', 'applicant_type': '普通車ＡＭ'},
    {'date': '06/05 (Thu)', 'facility': '外国免許四輪車', 'applicant_type': '普通車ＰＭ'},
    {'date': '06/05 (Thu)', 'facility': '外国免許四輪車', 'applicant_type': '準中型車ＡＭ'},
]


@pytest.mark.asyncio
async def test_kanagawa_checker_filters_to_target_slot_types():
    bot = make_bot()
    result = await bot.kanagawa_checker.process_available_slots(
        KANAGAWA_SLOTS_MIXED, send_notifications=False, filter_applicants=True
    )
    assert '普通車ＡＭ' in result
    assert '普通車ＰＭ' in result
    assert '準中型車ＡＭ' not in result


@pytest.mark.asyncio
async def test_kanagawa_checker_unfiltered_shows_all():
    bot = make_bot()
    result = await bot.kanagawa_checker.process_available_slots(
        KANAGAWA_SLOTS_MIXED, send_notifications=False, filter_applicants=False
    )
    assert '普通車ＡＭ' in result
    assert '準中型車ＡＭ' in result


# --- Saitama slot filtering ---


@pytest.mark.asyncio
async def test_saitama_checker_filters_to_target_slot_types():
    bot = make_bot()
    result = await bot.saitama_checker.process_available_slots(
        SAITAMA_MIXED_SLOTS, send_notifications=False, filter_applicants=True
    )
    assert '【１】１回目（初めて）' in result
    assert '【２】２回目以降' not in result
    assert '【３】免除国等' not in result


@pytest.mark.asyncio
async def test_saitama_checker_unfiltered_shows_all():
    bot = make_bot()
    result = await bot.saitama_checker.process_available_slots(
        SAITAMA_MIXED_SLOTS, send_notifications=False, filter_applicants=False
    )
    assert '【１】１回目（初めて）' in result
    assert '【２】２回目以降' in result
    assert '【３】免除国等' in result


# --- _resolve_keep_types ---

def test_resolve_keep_types_all_returns_none():
    bot = make_bot()
    assert bot._resolve_keep_types("all", "tokyo") is None
    assert bot._resolve_keep_types("all", "kanagawa") is None
    assert bot._resolve_keep_types("all", "saitama") is None


def test_resolve_keep_types_tokyo_ari():
    bot = make_bot()
    assert bot._resolve_keep_types("ari", "tokyo") == ["住民票のある方"]


def test_resolve_keep_types_tokyo_nai():
    bot = make_bot()
    assert bot._resolve_keep_types("nai", "tokyo") == ["住民票のない方"]


def test_resolve_keep_types_kanagawa_relevant_returns_both():
    bot = make_bot()
    result = bot._resolve_keep_types("relevant", "kanagawa")
    assert "普通車ＡＭ" in result
    assert "普通車ＰＭ" in result


def test_resolve_keep_types_kanagawa_am():
    bot = make_bot()
    assert bot._resolve_keep_types("am", "kanagawa") == ["普通車ＡＭ"]


def test_resolve_keep_types_kanagawa_pm():
    bot = make_bot()
    assert bot._resolve_keep_types("pm", "kanagawa") == ["普通車ＰＭ"]


def test_resolve_keep_types_saitama_relevant_returns_first_only():
    """Unlike Kanagawa's relevant-returns-both, Saitama's relevant default is first-time only."""
    bot = make_bot()
    assert bot._resolve_keep_types("relevant", "saitama") == ["【１】１回目（初めて）"]


def test_resolve_keep_types_saitama_1():
    bot = make_bot()
    assert bot._resolve_keep_types("1", "saitama") == ["【１】１回目（初めて）"]


def test_resolve_keep_types_saitama_2():
    bot = make_bot()
    assert bot._resolve_keep_types("2", "saitama") == ["【２】２回目以降"]


def test_resolve_keep_types_saitama_3():
    bot = make_bot()
    assert bot._resolve_keep_types("3", "saitama") == ["【３】免除国等"]


# --- Kanagawa slot-type filtering ---

CHECK_KANAGAWA_EXTRA = check_from_slots(
    [
        *KANAGAWA_SLOTS,
        {"date": "06/05 (Thu)", "facility": "外国免許四輪車", "applicant_type": "準中型車ＡＭ"},
    ],
    facilities_label=["外国免許四輪車"],
)


def test_filter_kanagawa_am_only():
    bot = make_bot()
    result = format_check_message(CHECK_KANAGAWA_EXTRA, keep_types=["普通車ＡＭ"])
    assert '普通車ＡＭ' in result
    assert '普通車ＰＭ' not in result
    assert '準中型車ＡＭ' not in result


def test_filter_kanagawa_pm_only():
    bot = make_bot()
    result = format_check_message(CHECK_KANAGAWA, keep_types=["普通車ＰＭ"])
    assert '普通車ＰＭ' in result
    assert '普通車ＡＭ' not in result


def test_filter_kanagawa_none_returns_all():
    bot = make_bot()
    result = format_check_message(CHECK_KANAGAWA, keep_types=None)
    assert "普通車ＡＭ" in result and "普通車ＰＭ" in result


# --- Saitama slot-type filtering ---


def test_filter_saitama_first_only():
    bot = make_bot()
    result = format_check_message(CHECK_SAITAMA_MIXED, keep_types=["【１】１回目（初めて）"])
    assert '【１】１回目（初めて）' in result
    assert '【２】２回目以降' not in result
    assert '【３】免除国等' not in result


def test_filter_saitama_none_returns_all():
    bot = make_bot()
    result = format_check_message(CHECK_SAITAMA_MIXED, keep_types=None)
    assert '【１】１回目（初めて）' in result
    assert '【２】２回目以降' in result
    assert '【３】免除国等' in result


# --- _parse_command_args source parsing ---

def test_parse_command_args_kanagawa():
    bot = make_bot()
    force, show_all, source = bot._parse_command_args(["kanagawa"])
    assert source == "kanagawa"
    assert not force
    assert not show_all


def test_parse_command_args_saitama():
    bot = make_bot()
    force, show_all, source = bot._parse_command_args(["saitama"])
    assert source == "saitama"
    assert not force
    assert not show_all


def test_parse_command_args_samezu():
    bot = make_bot()
    _, _, source = bot._parse_command_args(["samezu"])
    assert source == "samezu"


def test_parse_command_args_default_source_is_none():
    bot = make_bot()
    _, _, source = bot._parse_command_args([])
    assert source is None


def test_parse_command_args_kanagawa_force_all():
    bot = make_bot()
    force, show_all, source = bot._parse_command_args(["kanagawa", "force", "all"])
    assert source == "kanagawa"
    assert force
    assert show_all
