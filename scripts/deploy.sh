#!/usr/bin/env bash
# Deploy samezu_bot to the VPS: pull, run tests, restart systemd.
set -euo pipefail

SSH_KEY="${SSH_KEY:-$HOME/.ssh/samezu_bot2.key}"
HOST="${DEPLOY_HOST:-ubuntu@131.186.56.62}"
REMOTE_DIR="${REMOTE_DIR:-~/samezu_bot}"
SERVICE="${SERVICE:-samezu_bot}"

ssh -i "$SSH_KEY" "$HOST" bash -s <<EOF
set -euo pipefail
cd $REMOTE_DIR
git pull
if [ -d venv ]; then
  ./venv/bin/python -m pytest -q -m "not live"
else
  python3 -m pytest -q -m "not live"
fi
sudo systemctl restart $SERVICE
sudo systemctl status $SERVICE --no-pager
EOF
