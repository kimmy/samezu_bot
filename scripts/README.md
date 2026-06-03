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

Run locally for investigation (no Telegram):

```bash
cd "$(git rev-parse --show-toplevel)"
source venv/bin/activate
python scripts/reservation_checker_requests.py
```

Do not cron this script with real `subscribers.txt` on a shared token.
