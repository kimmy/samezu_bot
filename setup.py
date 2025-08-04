#!/usr/bin/env python3
"""
Setup script for Samezu Bot
Helps users configure their environment variables and create config.py
"""

import os
import json
import shutil

def create_config_from_template():
    """Create config.py from template if it doesn't exist"""
    if not os.path.exists('config.py'):
        if os.path.exists('config_template.py'):
            shutil.copy('config_template.py', 'config.py')
            print("✅ Created config.py from template")
            print("⚠️  Please update config.py with your actual bot token and chat IDs")
        else:
            print("❌ config_template.py not found")
            return False
    else:
        print("✅ config.py already exists")
    return True

def setup_environment_variables():
    """Guide user to set up environment variables"""
    print("\n🔧 Environment Variables Setup")
    print("=" * 40)
    
    print("\nTo use GitHub secrets (recommended):")
    print("1. Go to your GitHub repository")
    print("2. Navigate to Settings > Secrets and variables > Actions")
    print("3. Add these secrets:")
    print()
    print("   TELEGRAM_BOT_TOKEN:")
    print("   Value: your_bot_token_here")
    print()
    print("   TELEGRAM_USERS:")
    print("   Value: {\"YOUR_CHAT_ID\": {\"name\": \"Your Name\", \"notify_no_slots\": true, \"notify_slots\": true, \"notify_errors\": true}}")
    print()
    
    print("For local development, create a .env file:")
    print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
    print("TELEGRAM_USERS={\"YOUR_CHAT_ID\": {\"name\": \"Your Name\", \"notify_no_slots\": true, \"notify_slots\": true, \"notify_errors\": true}}")

def main():
    print("🚀 Samezu Bot Setup")
    print("=" * 40)
    
    # Create config.py from template
    if create_config_from_template():
        setup_environment_variables()
        
        print("\n✅ Setup complete!")
        print("\nNext steps:")
        print("1. Update config.py with your bot token and chat IDs")
        print("2. Or set up GitHub secrets for production")
        print("3. Run: python reservation_checker.py")
    else:
        print("❌ Setup failed")

if __name__ == "__main__":
    main() 
