"""Unit tests for domain slot filtering and rendering."""

from domain import (
    CheckResult,
    Slot,
    dedupe_slots,
    facilities_summary,
    filter_slots,
    format_check_message,
    render_slots_message,
    scheduler_notify_signature,
    slot_type_matches,
    slots_signature,
)
from tests.test_helpers import CHECK_TOKYO_BOTH, EXAMPLE_URL, check_from_slots


TOKYO_LONG_NAI = "29の国･地域以外の方で、住民票のない方"
TOKYO_LONG_ARI = "29の国･地域以外の方で、住民票のある方"


def test_slot_type_matches_tokyo_long_form_labels():
    assert slot_type_matches("住民票のない方", TOKYO_LONG_NAI)
    assert slot_type_matches("住民票のある方", TOKYO_LONG_ARI)
    assert not slot_type_matches("住民票のある方", TOKYO_LONG_NAI)
    assert not slot_type_matches("住民票のない方", TOKYO_LONG_ARI)


def test_filter_slots_tokyo_long_form_nai():
    check = check_from_slots(
        [{"date": "08/21 (Thu)", "facility": "鮫洲試験場", "applicant_type": TOKYO_LONG_NAI}],
        facilities_label=["鮫洲試験場"],
    )
    result = format_check_message(check, keep_types=["住民票のない方"])
    assert "08/21" in result
    assert TOKYO_LONG_NAI in result
    assert "❌ No slots found" not in result


def test_filter_slots_tokyo_long_form_ari_relevant():
    check = check_from_slots(
        [{"date": "08/21 (Thu)", "facility": "鮫洲試験場", "applicant_type": TOKYO_LONG_ARI}],
        facilities_label=["鮫洲試験場"],
    )
    result = format_check_message(check, keep_types=["住民票のある方"])
    assert "08/21" in result
    assert TOKYO_LONG_ARI in result


def test_filter_slots_by_type_exact_match():
    slots = [
        Slot("06/05", "鮫洲試験場", "住民票のある方"),
        Slot("06/05", "鮫洲試験場", "住民票のない方"),
    ]
    filtered = filter_slots(slots, keep_types=["住民票のある方"])
    assert len(filtered) == 1
    assert filtered[0].applicant_type == "住民票のある方"


def test_filter_slots_by_facility():
    slots = [
        Slot("06/05", "鮫洲試験場", "住民票のある方"),
        Slot("06/05", "府中試験場", "住民票のある方"),
    ]
    filtered = filter_slots(slots, keep_facilities=["鮫洲試験場"])
    assert len(filtered) == 1
    assert filtered[0].facility == "鮫洲試験場"


def test_format_check_message_error_passthrough():
    check = CheckResult.from_error("❌ Error during reservation check: timeout", target_url=EXAMPLE_URL)
    assert format_check_message(check) == "❌ Error during reservation check: timeout"


def test_format_check_message_no_slots():
    check = CheckResult.no_slots(target_url=EXAMPLE_URL)
    assert format_check_message(check) == "❌ No slots"


def test_render_escapes_html():
    slots = [Slot("06/05 <x>", "施設 & 名", "タイプ")]
    msg = render_slots_message(slots, facilities_label=["施設 & 名"], target_url=EXAMPLE_URL)
    assert "&amp;" in msg
    assert "<x>" not in msg


def test_facilities_summary_reflects_slots_not_stale_scope():
    slots = [Slot("06/05", "鮫洲試験場", "住民票のある方")]
    assert facilities_summary(slots, preferred_order=["府中試験場", "鮫洲試験場"]) == "鮫洲試験場"


def test_format_check_message_facilities_header_matches_filtered_body():
    result = format_check_message(CHECK_TOKYO_BOTH, keep_facilities=["鮫洲試験場"])
    assert "📍 <b>Facilities:</b> 鮫洲試験場" in result
    assert "府中試験場" not in result.split("To book")[0]


def test_dedupe_slots_collapses_overlapping_pages():
    duplicate = Slot("08/13(Thu)", "外国免許四輪車", "普通車ＡＭ")
    merged = dedupe_slots([duplicate, duplicate])
    assert len(merged) == 1
    assert slots_signature([duplicate, duplicate]) == slots_signature([duplicate])


def test_scheduler_notify_signature_ignores_rendering():
    from config_template import TARGET_SLOT_TYPES

    sig = scheduler_notify_signature(CHECK_TOKYO_BOTH, default_slot_types=TARGET_SLOT_TYPES)
    assert sig == slots_signature(
        filter_slots(CHECK_TOKYO_BOTH.slots, keep_types=TARGET_SLOT_TYPES)
    )
