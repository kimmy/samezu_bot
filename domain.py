"""Typed reservation slots and message formatting (Phase B)."""

from __future__ import annotations

import html
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple, Union

NO_SLOTS_MESSAGE = "❌ No slots"


@dataclass(frozen=True)
class Slot:
    date: str
    facility: str
    applicant_type: str

    @classmethod
    def from_mapping(cls, data: dict) -> Slot:
        return cls(
            date=data["date"],
            facility=data["facility"],
            applicant_type=data["applicant_type"],
        )


@dataclass(frozen=True)
class CheckResult:
    """Outcome of one scrape: slots, empty calendar, or error."""

    slots: Tuple[Slot, ...] = field(default_factory=tuple)
    error: Optional[str] = None
    target_url: str = ""
    facilities_label: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_error(self) -> bool:
        return self.error is not None

    @property
    def has_slots(self) -> bool:
        return bool(self.slots) and not self.is_error

    @classmethod
    def no_slots(cls, *, target_url: str = "", facilities_label: Sequence[str] = ()) -> CheckResult:
        return cls(target_url=target_url, facilities_label=tuple(facilities_label))

    @classmethod
    def from_error(
        cls,
        message: str,
        *,
        target_url: str = "",
        facilities_label: Sequence[str] = (),
    ) -> CheckResult:
        return cls(error=message, target_url=target_url, facilities_label=tuple(facilities_label))

    @classmethod
    def from_slots(
        cls,
        slots: Iterable[Union[Slot, dict]],
        *,
        target_url: str = "",
        facilities_label: Sequence[str] = (),
    ) -> CheckResult:
        normalized: List[Slot] = []
        for item in slots:
            if isinstance(item, Slot):
                normalized.append(item)
            else:
                normalized.append(Slot.from_mapping(item))
        return cls(
            slots=dedupe_slots(normalized),
            target_url=target_url,
            facilities_label=tuple(facilities_label),
        )


def normalize_label(text: str) -> str:
    return " ".join(text.strip().split())


def slot_type_matches(keep_type: str, applicant_type: str) -> bool:
    """Match a filter token against a scraped applicant_type label.

    Tokyo rows use long labels (e.g. ``29の国･地域以外の方で、住民票のない方``) while
    subscription filters use the short suffix (``住民票のない方``). Kanagawa types
    use exact full-width labels (``普通車ＡＭ`` / ``普通車ＰＭ``).
    """
    normalized_type = normalize_label(applicant_type)
    normalized_keep = normalize_label(keep_type)
    if normalized_type == normalized_keep:
        return True
    return normalized_keep in normalized_type


def slot_key(slot: Slot) -> Tuple[str, str, str]:
    return (normalize_label(slot.date), slot.facility, normalize_label(slot.applicant_type))


def dedupe_slots(slots: Iterable[Slot]) -> Tuple[Slot, ...]:
    """Collapse duplicate date/facility/type rows (e.g. overlapping calendar pages)."""
    seen: set[Tuple[str, str, str]] = set()
    unique: List[Slot] = []
    for slot in slots:
        key = slot_key(slot)
        if key in seen:
            continue
        seen.add(key)
        unique.append(slot)
    return tuple(unique)


def filter_slots(
    slots: Iterable[Slot],
    *,
    keep_types: Optional[Sequence[str]] = None,
    keep_facilities: Optional[Sequence[str]] = None,
) -> List[Slot]:
    """Return slots matching optional type and facility filters."""
    result = list(slots)
    if keep_types is not None:
        result = [
            s
            for s in result
            if any(slot_type_matches(keep_type, s.applicant_type) for keep_type in keep_types)
        ]
    if keep_facilities is not None:
        keep_set = set(keep_facilities)
        result = [s for s in result if s.facility in keep_set]
    return result


def no_slots_message_for_filter(names: Sequence[str]) -> str:
    return f"❌ No slots found for {', '.join(names)}"


def facilities_summary(
    slots: Sequence[Slot],
    preferred_order: Sequence[str] = (),
) -> str:
    """Facilities line for the message header — always reflects slots in the body."""
    present = {s.facility for s in slots}
    if not present:
        return ""
    if preferred_order:
        ordered = [name for name in preferred_order if name in present]
        if ordered:
            return ", ".join(ordered)
    return ", ".join(sorted(present))


def render_slots_message(
    slots: Sequence[Slot],
    *,
    facilities_label: Sequence[str] = (),
    target_url: str,
) -> str:
    """Format slots as Telegram HTML (empty slots → empty string)."""
    if not slots:
        return ""

    slots_by_date_facility: dict = {}
    for slot in slots:
        slots_by_date_facility.setdefault(slot.date, {}).setdefault(slot.facility, []).append(
            slot.applicant_type
        )

    label = facilities_summary(slots, preferred_order=facilities_label)

    message = "🎉 <b>Available Reservation Slots Found!</b>\n\n"
    message += f"📍 <b>Facilities:</b> {html.escape(label)}\n\n"
    message += (
        "<b>To book, click the <i>予約可能 (reservable)</i> or <i>選択中 (selected)</i> "
        "mark on your desired date on the calendar. Then proceed with the booking process.</b>\n\n"
    )

    for date, facilities in slots_by_date_facility.items():
        message += f"📅 <b>{html.escape(date)}</b>\n"
        for facility, applicant_types in facilities.items():
            message += f"   🏢 <b>{html.escape(facility)}</b>\n"
            for applicant_type in applicant_types:
                message += f"      • {html.escape(applicant_type)}\n"
        message += "\n"

    if target_url:
        message += f"🔗 <a href='{target_url}'>Book Now</a>"

    return message


def format_check_message(
    check: CheckResult,
    *,
    keep_types: Optional[Sequence[str]] = None,
    keep_facilities: Optional[Sequence[str]] = None,
    apply_default_types: Optional[Sequence[str]] = None,
) -> str:
    """Render a CheckResult with optional filters (errors and no-slots pass through)."""
    if check.is_error:
        return check.error or NO_SLOTS_MESSAGE
    if not check.has_slots:
        return NO_SLOTS_MESSAGE

    slots = list(check.slots)
    if apply_default_types is not None:
        slots = filter_slots(slots, keep_types=apply_default_types)
    if keep_types is not None:
        slots = filter_slots(slots, keep_types=keep_types)
    if keep_facilities is not None:
        slots = filter_slots(slots, keep_facilities=keep_facilities)

    if not slots:
        if keep_facilities is not None:
            return no_slots_message_for_filter(keep_facilities)
        if keep_types is not None:
            return no_slots_message_for_filter(keep_types)
        if apply_default_types is not None:
            return no_slots_message_for_filter(apply_default_types)
        return NO_SLOTS_MESSAGE

    rendered = render_slots_message(
        slots,
        facilities_label=check.facilities_label,
        target_url=check.target_url,
    )
    return rendered or NO_SLOTS_MESSAGE


def slots_signature(slots: Sequence[Slot]) -> Tuple[Tuple[str, str, str], ...]:
    """Stable tuple for comparing slot sets (e.g. scheduler dedup)."""
    return tuple(sorted(slot_key(s) for s in dedupe_slots(slots)))


def scheduler_notify_signature(
    check: CheckResult,
    *,
    default_slot_types: Sequence[str],
) -> Optional[Tuple[Tuple[str, str, str], ...]]:
    """Relevant slot set for scheduler duplicate suppression (not rendered HTML)."""
    if not check.has_slots:
        return None
    filtered = filter_slots(check.slots, keep_types=list(default_slot_types))
    if not filtered:
        return None
    return slots_signature(filtered)
