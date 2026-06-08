# Operational risks

Known gaps between “tests pass” and “production stays correct on the live site.”

## Live site vs CI

| Risk | Mitigation today | Planned |
|------|------------------|---------|
| **DOM / markup changes** | `tests/test_playwright_fixtures.py` runs Playwright against saved `#TBL` HTML; `tests/test_fixtures.py` mirrors parser logic | Re-capture fixtures when markup changes (`scripts/capture_calendar_fixture.py`) |
| **Cloudflare waiting room** | Playwright wait loop (up to ~3 min); VPS-only observation | Optional `LIVE_SCRAPE=1 pytest -m live` smoke |
| **No live Playwright in default pytest** | By design (flaky, network); deploy runs full suite on VPS | `tests/test_live_scrape.py` (`@pytest.mark.live`) for manual/VPS checks |

Default `pytest` does **not** hit the reservation websites. Playwright fixture tests skip automatically if Chromium is not installed (`tests/conftest.py`). A green run proves fixture HTML still parses through **production selectors** when a browser is available, not that today's live calendar is unchanged.

Optional live smoke:

```bash
LIVE_SCRAPE=1 ./venv/bin/python -m pytest tests/test_live_scrape.py -m live -v
```

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
4. Check `last_notified` behavior: unchanged **slot signatures** suppress repeat alerts (message template changes do not re-notify).
