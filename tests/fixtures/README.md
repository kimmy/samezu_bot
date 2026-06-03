# HTML fixtures

Saved calendar markup for parser tests (Phase D). Not used by live Playwright checks yet.

| File | Description |
|------|-------------|
| `tokyo_calendar_sample.html` | Tokyo calendar table (`#TBL`) with `aria-label="予約可能"` |
| `kanagawa_calendar_sample.html` | Kanagawa calendar table captured from live site (e-kanagawa) |

### Refresh fixtures

```bash
source venv/bin/activate
python scripts/capture_calendar_fixture.py kanagawa
python scripts/capture_calendar_fixture.py tokyo   # overwrites Tokyo sample
```

Run when the site markup changes or to refresh date columns. Requires network + Playwright.
