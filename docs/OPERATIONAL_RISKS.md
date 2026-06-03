# Operational risks

Known gaps between “tests pass” and “production stays correct on the live site.”

## Live site vs CI

| Risk | Mitigation today | Planned |
|------|------------------|---------|
| **DOM / markup changes** | Manual checks; logs in `reservation_checker.log` | HTML fixture tests + pure parser (Phase D) |
| **Cloudflare waiting room** | Playwright wait loop (up to ~3 min); VPS-only observation | Classified errors + optional VPS smoke job |
| **No live Playwright in CI** | By design (flaky); hermetic unit tests only | Fixtures in GitHub Actions; live smoke on VPS optional |

`pytest` from repo root does **not** hit the reservation websites. A green CI run does not prove the calendar still parses correctly.

## Telegram delivery

| Risk | Mitigation |
|------|------------|
| **Standalone scraper notifies everyone** | Playwright and `scripts/reservation_checker_requests.py`: `send_notifications=True` requires `ALLOW_STANDALONE_NOTIFY=1`; CLI defaults print only. |
| **Two bot instances** | Never run local `run_bot.py` while VPS systemd service is polling the same token. |

Production notifications must go through `run_bot.py` so source, facility, and subscription-type filters apply.

## Deployment

- Use `./scripts/deploy.sh` (pull → `pytest` → `systemctl restart`).
- After deploy, confirm both `bot.log` and `reservation_checker.log` receive lines.
- If alerts look wrong, compare scheduler source (`tokyo`/`kanagawa`) with subscriber lines in `subscribers.txt` — see [CONTRACT.md](./CONTRACT.md).

## Debugging a missed alert (< 5 minutes)

1. `sudo journalctl -u samezu_bot -n 100 --no-pager`
2. `tail -n 100 bot.log reservation_checker.log`
3. Confirm subscriber `sources`/`type` match the slot that appeared.
4. Check `last_notified` behavior: unchanged slot text suppresses repeat alerts.
