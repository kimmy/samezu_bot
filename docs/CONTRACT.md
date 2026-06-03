# Samezu Bot — runtime contract

This document describes how sources, scraping, caching, and notifications behave in production (`run_bot.py` + systemd). Code should match this; tests should guard it.

## Production entrypoint

- **Run only** `python run_bot.py` (or the `samezu_bot` systemd unit) on the VPS.
- Do **not** schedule `reservation_checker_playwright.py` or `scripts/reservation_checker_requests.py` with Telegram notifications enabled.

## Source model (hybrid)

Two vocabularies are intentional until a typed `Source` enum replaces them.

| Layer | Keys | Meaning |
|-------|------|---------|
| **Scrape / scheduler** | `tokyo`, `kanagawa` | One Playwright check per key; `check_lock` and `waiting_users` use these. |
| **Subscriber / commands** | `samezu`, `fuchu`, `kanagawa` | User preferences; `samezu` + `fuchu` both map to scheduler source `tokyo`. |

### Mapping

| Subscriber source | Scheduler / notify `source` | Facility (when filtered) |
|-------------------|----------------------------|---------------------------|
| `samezu` | `tokyo` | 鮫洲試験場 |
| `fuchu` | `tokyo` | 府中試験場 |
| `kanagawa` | `kanagawa` | 外国免許四輪車 |
| both `samezu` + `fuchu` | `tokyo` | no per-facility filter (all Tokyo facilities) |

`_subscriber_matches_source()` implements the Tokyo ↔ samezu/fuchu routing for notifications.

## Scraping

- **Production scraper:** `reservation_checker_playwright.py` (`ReservationChecker`).
- **Experimental:** `scripts/reservation_checker_requests.py` (HTTP; not wired to the bot).

Each checker instance has its own `target_url`, `target_facilities`, `target_slot_types`, and `source_name` (`tokyo` or `kanagawa`).

## Cache

- One cache dict per scrape key: `cache` (Tokyo), `kanagawa_cache` (Kanagawa).
- Stores **formatted HTML results** today (slot-object cache is planned).
- Metadata: `use_month_navigation` must match for cache hits (`/check` vs `/check_month`).
- TTL: `CACHE_DURATION` (default 120s).

## Scheduler

- On bot start, runs Tokyo + Kanagawa scrapes **immediately**, then every `CHECK_INTERVAL` seconds (default 300).
- Updates both caches even when the result is `❌ No slots` or an error string.

## Notifications

- Scheduler runs checks with `send_notifications=False` on the scraper.
- Delivery goes through `_send_notifications_to_subscribers()` with per-subscriber:
  - source match (`tokyo` / `kanagawa`)
  - facility filter (samezu/fuchu only)
  - slot-type filter (`relevant`, `ari`, `nai`, `am`, `pm`, `all`)
- `last_notified[source]` suppresses duplicate alerts until slots change or disappear.

## Manual `/check`

- Wait queue keyed by scrape key (`tokyo` / `kanagawa`).
- Incompatible waiters are re-queued; chained background scrapes drain remaining keys.
- `force` bypasses cache; cached results never satisfy a forced check.

## Subscriber file

`subscribers.txt`: `chat_id|username|sources|type`

- `sources`: comma-separated `samezu`, `fuchu`, `kanagawa` (legacy 2-field lines default to all three).
- `type`: `relevant` (default), `all`, `nai`, `ari`, `am`, `pm`.
