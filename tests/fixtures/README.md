# HTML fixtures

Saved calendar markup for parser tests (Phase D). Not used by live Playwright checks yet.

| File | Description |
|------|-------------|
| `tokyo_calendar_sample.html` | Tokyo calendar table (`#TBL`) with `aria-label="予約可能"` |
| `kanagawa_calendar_sample.html` | Kanagawa week with open slots (08/09–08/22, 2026; includes `予約可能` on 08/13–08/14) |

### Refresh fixtures

```bash
source venv/bin/activate
python scripts/capture_calendar_fixture.py kanagawa
python scripts/capture_calendar_fixture.py tokyo   # overwrites Tokyo sample
```

Run when the site markup changes or to refresh date columns. Requires network + Playwright.

If auto-capture lands on a week with no open slots, paste the live `#TBL` outer HTML into `kanagawa_calendar_sample.html` (or re-run capture after advancing the calendar).
