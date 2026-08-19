"""Shared CheckResult fixtures for bot tests."""

from domain import CheckResult

EXAMPLE_URL = "http://example.com"


def check_no_slots(*, facilities_label=()):
    return CheckResult.no_slots(target_url=EXAMPLE_URL, facilities_label=tuple(facilities_label))


def check_error(message: str):
    return CheckResult.from_error(message, target_url=EXAMPLE_URL)


def check_from_slots(slots, *, facilities_label=()):
    return CheckResult.from_slots(
        slots,
        target_url=EXAMPLE_URL,
        facilities_label=tuple(facilities_label),
    )


TOKYO_ARI_SLOT = {
    "date": "2026-03-20",
    "facility": "鮫洲試験場",
    "applicant_type": "住民票のある方",
}

TOKYO_MIXED_SLOTS = [
    {"date": "06/05 (Thu)", "facility": "鮫洲試験場", "applicant_type": "住民票のある方"},
    {"date": "06/05 (Thu)", "facility": "鮫洲試験場", "applicant_type": "住民票のない方"},
]

TOKYO_BOTH_FACILITIES_SLOTS = [
    {"date": "06/05 (Thu)", "facility": "鮫洲試験場", "applicant_type": "住民票のある方"},
    {"date": "06/05 (Thu)", "facility": "府中試験場", "applicant_type": "住民票のある方"},
]

TOKYO_SPLIT_TYPES_SLOTS = [
    {"date": "06/05 (Thu)", "facility": "鮫洲試験場", "applicant_type": "住民票のない方"},
    {"date": "06/05 (Thu)", "facility": "府中試験場", "applicant_type": "住民票のある方"},
]

KANAGAWA_SLOTS = [
    {"date": "06/05 (Thu)", "facility": "外国免許四輪車", "applicant_type": "普通車ＡＭ"},
    {"date": "06/05 (Thu)", "facility": "外国免許四輪車", "applicant_type": "普通車ＰＭ"},
]

SAITAMA_FIRST_SLOT = {
    "date": "06/05 (Thu)",
    "facility": "外免　書類審査",
    "applicant_type": "【１】１回目（初めて）",
}
SAITAMA_REPEAT_SLOT = {
    "date": "06/05 (Thu)",
    "facility": "外免　書類審査",
    "applicant_type": "【２】２回目以降",
}
SAITAMA_EXEMPT_SLOT = {
    "date": "06/05 (Thu)",
    "facility": "外免　書類審査",
    "applicant_type": "【３】免除国等",
}
SAITAMA_SLOTS = [SAITAMA_FIRST_SLOT]
SAITAMA_MIXED_SLOTS = [SAITAMA_FIRST_SLOT, SAITAMA_REPEAT_SLOT, SAITAMA_EXEMPT_SLOT]

CHECK_TOKYO_ARI = check_from_slots(
    [TOKYO_ARI_SLOT],
    facilities_label=["鮫洲試験場", "府中試験場"],
)
CHECK_NO_SLOTS = check_no_slots()
CHECK_KANAGAWA = check_from_slots(KANAGAWA_SLOTS, facilities_label=["外国免許四輪車"])
CHECK_SAITAMA = check_from_slots(SAITAMA_SLOTS, facilities_label=["外免　書類審査"])
CHECK_SAITAMA_MIXED = check_from_slots(SAITAMA_MIXED_SLOTS, facilities_label=["外免　書類審査"])
CHECK_TOKYO_BOTH = check_from_slots(
    TOKYO_BOTH_FACILITIES_SLOTS,
    facilities_label=["府中試験場", "鮫洲試験場"],
)
CHECK_TOKYO_MIXED = check_from_slots(
    TOKYO_MIXED_SLOTS,
    facilities_label=["鮫洲試験場"],
)
CHECK_TOKYO_SPLIT = check_from_slots(
    TOKYO_SPLIT_TYPES_SLOTS,
    facilities_label=["府中試験場", "鮫洲試験場"],
)
