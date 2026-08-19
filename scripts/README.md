# Scripts

## `deploy.sh`

Production deploy: SSH to VPS, `git pull`, run `pytest`, restart `samezu_bot` systemd.

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Override host/key via `DEPLOY_HOST`, `SSH_KEY`, `REMOTE_DIR`, `SERVICE`.

## `reservation_checker_requests.py`

**Experimental — not used in production.**

HTTP + BeautifulSoup prototype for Tokyo. Does not handle Cloudflare/browser flows reliably. The bot uses `reservation_checker_playwright.py` only.

Run locally for investigation (no Telegram; prints to stdout):

```bash
cd "$(git rev-parse --show-toplevel)"
source venv/bin/activate
python scripts/reservation_checker_requests.py
```

Same guard as Playwright: enabling Telegram requires `ALLOW_STANDALONE_NOTIFY=1` and `send_notifications=True` in code — not used by the CLI. Do not cron this script against production `subscribers.txt`.

For live Playwright debugging from repo root:

```bash
python reservation_checker_playwright.py
```

## `capture_calendar_fixture.py`

Save the live reservation table HTML into `tests/fixtures/` (for parser tests):

```bash
python scripts/capture_calendar_fixture.py kanagawa
python scripts/capture_calendar_fixture.py tokyo
python scripts/capture_calendar_fixture.py saitama
```
