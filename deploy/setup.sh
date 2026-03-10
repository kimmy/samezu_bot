#!/bin/bash
# Run this once on a fresh Oracle Cloud Ubuntu VM to set up the bot

set -e

echo "=== Updating system ==="
sudo apt-get update && sudo apt-get upgrade -y

echo "=== Installing Python and dependencies ==="
sudo apt-get install -y python3 python3-pip python3-venv git

echo "=== Cloning repo ==="
# Replace with your actual GitHub repo URL if you have one,
# or we'll copy files manually via scp
# git clone https://github.com/YOUR_USERNAME/samezu_bot.git ~/samezu_bot

echo "=== Setting up Python virtual environment ==="
cd ~/samezu_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo "=== Installing Playwright Chromium ==="
playwright install chromium
playwright install-deps chromium

echo "=== Setup complete ==="
echo "Next: set your TELEGRAM_BOT_TOKEN in /etc/systemd/system/samezu_bot.service"
