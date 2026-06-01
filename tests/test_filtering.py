import pytest
from run_bot import SamezuBot


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
async def test_process_slots_returns_no_slots_when_filtered_out():
    bot = make_bot()
    result = await bot.reservation_checker.process_available_slots(TOKYO_SLOTS_NAI_ONLY, send_notifications=False, filter_applicants=True)
    assert '❌' in result
    # No booking lines should appear — the string only appears in the "no slots" explanation
    assert '— <a href=' not in result


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

FORMATTED_MIXED = (
    "🎉 <b>Available Reservation Slots Found!</b>\n\n"
    "📍 <b>Facilities:</b> 鮫洲試験場\n\n"
    "<b>To book, click the <i>予約可能 (reservable)</i> or <i>選択中 (selected)</i> mark on your desired date on the calendar. Then proceed with the booking process.</b>\n\n"
    "📅 <b>06/05 (Thu)</b>\n"
    "   🏢 <b>鮫洲試験場</b>\n"
    "      • 住民票のある方 — <a href='http://example.com'>Book</a>\n"
    "      • 住民票のない方 — <a href='http://example.com'>Book</a>\n"
    "\n"
    "🔗 <a href='http://example.com'>Book Now</a>"
)


@pytest.mark.asyncio
async def test_filter_subscription_all_returns_both_types():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(FORMATTED_MIXED, "all", source="tokyo")
    assert '住民票のある方' in result
    assert '住民票のない方' in result


@pytest.mark.asyncio
async def test_filter_subscription_ari_keeps_ari_removes_nai():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(FORMATTED_MIXED, "ari", source="tokyo")
    assert '住民票のある方' in result
    assert '住民票のない方' not in result


@pytest.mark.asyncio
async def test_filter_subscription_nai_keeps_nai_removes_ari():
    bot = make_bot()
    result = await bot._filter_result_for_subscription(FORMATTED_MIXED, "nai", source="tokyo")
    assert '住民票のない方' in result
    assert '住民票のある方' not in result


@pytest.mark.asyncio
async def test_filter_subscription_relevant_same_as_ari():
    bot = make_bot()
    ari = await bot._filter_result_for_subscription(FORMATTED_MIXED, "ari", source="tokyo")
    relevant = await bot._filter_result_for_subscription(FORMATTED_MIXED, "relevant", source="tokyo")
    assert ari == relevant


@pytest.mark.asyncio
async def test_filter_subscription_passes_through_no_slots():
    bot = make_bot()
    no_slots = "❌ No slots"
    result = await bot._filter_result_for_subscription(no_slots, "ari", source="tokyo")
    assert result == no_slots


@pytest.mark.asyncio
async def test_filter_subscription_passes_through_error():
    bot = make_bot()
    error = "❌ Error during reservation check: timeout"
    result = await bot._filter_result_for_subscription(error, "all", source="tokyo")
    assert result == error


# --- Subscriber round-trip ---

def test_add_and_get_subscriber(tmp_path, monkeypatch):
    bot = make_bot()
    monkeypatch.setattr(bot, 'SUBSCRIBERS_FILE', str(tmp_path / 'subscribers.txt'))
    bot.add_subscriber(99999, "@alice|relevant")
    subs = bot.get_subscribers()
    assert any(s[0] == '99999' for s in subs)


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


# --- _resolve_keep_types ---

def test_resolve_keep_types_all_returns_none():
    bot = make_bot()
    assert bot._resolve_keep_types("all", "tokyo") is None
    assert bot._resolve_keep_types("all", "kanagawa") is None


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


# --- Kanagawa result filtering via _filter_result_by_slot_types ---

FORMATTED_KANAGAWA = (
    "🎉 <b>Available Reservation Slots Found!</b>\n\n"
    "📍 <b>Facilities:</b> 外国免許四輪車\n\n"
    "<b>To book, click the <i>予約可能 (reservable)</i> or <i>選択中 (selected)</i> mark on your desired date on the calendar. Then proceed with the booking process.</b>\n\n"
    "📅 <b>06/05 (Thu)</b>\n"
    "   🏢 <b>外国免許四輪車</b>\n"
    "      • 普通車ＡＭ — <a href='http://example.com'>Book</a>\n"
    "      • 普通車ＰＭ — <a href='http://example.com'>Book</a>\n"
    "      • 準中型車ＡＭ — <a href='http://example.com'>Book</a>\n"
    "\n"
    "🔗 <a href='http://example.com'>Book Now</a>"
)


def test_filter_kanagawa_am_only():
    bot = make_bot()
    result = bot._filter_result_by_slot_types(FORMATTED_KANAGAWA, ["普通車ＡＭ"])
    assert '普通車ＡＭ' in result
    assert '普通車ＰＭ' not in result
    assert '準中型車ＡＭ' not in result


def test_filter_kanagawa_pm_only():
    bot = make_bot()
    result = bot._filter_result_by_slot_types(FORMATTED_KANAGAWA, ["普通車ＰＭ"])
    assert '普通車ＰＭ' in result
    assert '普通車ＡＭ' not in result


def test_filter_kanagawa_none_returns_all():
    bot = make_bot()
    result = bot._filter_result_by_slot_types(FORMATTED_KANAGAWA, None)
    assert result == FORMATTED_KANAGAWA


# --- _parse_command_args source parsing ---

def test_parse_command_args_kanagawa():
    bot = make_bot()
    force, show_all, source = bot._parse_command_args(["kanagawa"])
    assert source == "kanagawa"
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
