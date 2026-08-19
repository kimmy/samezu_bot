# HTML fixtures

Saved calendar markup for parser tests (Phase D). Not used by live Playwright checks yet.

| File | Description |
|------|-------------|
| `tokyo_calendar_sample.html` | Tokyo calendar table (`#TBL`) with `aria-label="予約可能"` |
| `kanagawa_calendar_sample.html` | Kanagawa week with open slots (08/09–08/22, 2026; includes `予約可能` on 08/13–08/14) |
| `saitama_calendar_sample.html` | Saitama week, 08/23–09/05 2026. `【１】１回目（初めて）` has a real captured `予約可能` on 08/26; `【２】２回目以降` and `【３】免除国等` had none live, so one `空き無` cell each was hand-flipped to `予約可能` on 08/27 to exercise all three rowspan-carried-forward sub-rows |

### Refresh fixtures

```bash
source venv/bin/activate
python scripts/capture_calendar_fixture.py kanagawa
python scripts/capture_calendar_fixture.py tokyo   # overwrites Tokyo sample
python scripts/capture_calendar_fixture.py saitama
```

Run when the site markup changes or to refresh date columns. Requires network + Playwright.

If auto-capture lands on a week with no open slots, paste the live `#TBL` outer HTML into the sample file (or re-run capture after advancing the calendar). If it still has no open slots for a sub-row you need covered, hand-flip one `aria-label="空き無"` (or `"時間外"`) to `"予約可能"` on a date cell under that sub-row — this is how `saitama_calendar_sample.html`'s `【２】` and `【３】` rows were seeded.
