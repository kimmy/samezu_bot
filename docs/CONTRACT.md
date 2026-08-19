# Samezu Bot — runtime contract

This document describes how sources, scraping, caching, and notifications behave in production (`run_bot.py` + systemd). Code should match this; tests should guard it.

## Production entrypoint

- **Run only** `python run_bot.py` (or the `samezu_bot` systemd unit) on the VPS.
- Do **not** schedule `reservation_checker_playwright.py` or `scripts/reservation_checker_requests.py` with Telegram notifications enabled.

## Source model (hybrid)

Two vocabularies are intentional until a typed `Source` enum replaces them.

| Layer | Keys | Meaning |
|-------|------|---------|
| **Scrape / scheduler** | `tokyo`, `kanagawa`, `saitama` | One Playwright check per key; `check_lock` and `waiting_users` use these. |
| **Subscriber / commands** | `samezu`, `fuchu`, `kanagawa`, `saitama` | User preferences; `samezu` + `fuchu` both map to scheduler source `tokyo`. `saitama` is opt-in only — never included in a default/legacy "all sources" subscription. |

### Mapping

| Subscriber source | Scheduler / notify `source` | Facility (when filtered) |
|-------------------|----------------------------|---------------------------|
| `samezu` | `tokyo` | 鮫洲試験場 |
| `fuchu` | `tokyo` | 府中試験場 |
| `kanagawa` | `kanagawa` | 外国免許四輪車 |
| `saitama` | `saitama` | 外免　書類審査 (single facility, no filter) |
| both `samezu` + `fuchu` | `tokyo` | no per-facility filter (all Tokyo facilities) |

`_subscriber_matches_source()` implements the Tokyo ↔ samezu/fuchu routing for notifications.

## Scraping

- **Production scraper:** `reservation_checker_playwright.py` (`ReservationChecker`).
- **Experimental:** `scripts/reservation_checker_requests.py` (HTTP; not wired to the bot).

Each checker instance has its own `target_url`, `target_facilities`, `target_slot_types`, and `source_name` (`tokyo`, `kanagawa`, or `saitama`).

## Cache

- One cache dict per scrape key: `cache` (Tokyo), `kanagawa_cache` (Kanagawa), `saitama_cache` (Saitama).
- Stores a **`CheckResult`** (`domain.py`: `slots`, optional `error`, `target_url`, `facilities_label`). Telegram HTML is rendered at read time via `format_check_message()`. **Error results are not cached**; `/check` never serves a cached error.
- Metadata: `use_month_navigation` must match for cache hits (`/check` vs `/check_month`).
- TTL: `CACHE_DURATION` (default 120s).

## Scheduler

- On bot start, runs Tokyo + Kanagawa + Saitama scrapes **immediately**, then every `CHECK_INTERVAL` seconds (default 300).
- Updates the cache on a **successful** scrape, including when the result is `❌ No slots`.
- On scrape **errors**, leaves the existing cache and `last_notified` unchanged (see Cache and Notifications).

## Notifications

- Scheduler runs checks with `send_notifications=False` on the scraper.
- Delivery goes through `_send_notifications_to_subscribers()` with per-subscriber:
  - source match (`tokyo` / `kanagawa` / `saitama`)
  - facility filter (samezu/fuchu only)
  - slot-type filter (`relevant`, `ari`, `nai`, `am`, `pm`, `1`, `2`, `3`, `all`)
- `last_notified[source]` stores a **slot signature** (`scheduler_notify_signature`: relevant types only), not rendered HTML. Duplicate alerts are suppressed until the slot set changes or disappears. **Transient scrape errors do not clear** `last_notified` (only a successful empty scrape does).
- Signatures persist in `last_notified.json` (same directory as `subscribers.txt`) so restarts do not re-alert for unchanged slots.

## Manual `/check`

- Wait queue keyed by scrape key (`tokyo` / `kanagawa` / `saitama`).
- Incompatible waiters are re-queued; chained background scrapes drain remaining keys.
- `force` bypasses cache; cached results never satisfy a forced check.

## Subscriber file

`subscribers.txt`: `chat_id|username|sources|type`

- `sources`: comma-separated `samezu`, `fuchu`, `kanagawa`, `saitama` (legacy 2-field lines default to `samezu`, `fuchu`, `kanagawa` — `saitama` is opt-in only and never included by default).
- `type`: `relevant` (default), `all`, `nai`, `ari`, `am`, `pm`, `1`, `2`, `3` (`1`/`2`/`3` are Saitama-only: 【１】１回目（初めて）/【２】２回目以降/【３】免除国等).
