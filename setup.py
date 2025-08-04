#!/usr/bin/env python3
"""
Setup script for Tokyo Police Department Reservation Checker
Helps users create their configuration file securely.
"""

import os
import shutil

def main():
    print("🔧 Setting up Tokyo Police Department Reservation Checker")
    print("=" * 50)
    
    # Check if config.py already exists
    if os.path.exists("config.py"):
        print("⚠️  config.py already exists!")
        overwrite = input("Do you want to overwrite it? (y/n): ").strip().lower()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    # Copy template to config.py
    if os.path.exists("config_template.py"):
        shutil.copy("config_template.py", "config.py")
        print("✅ Created config.py from template")
    else:
        print("❌ config_template.py not found!")
        return
    
    print("\n📝 Next steps:")
    print("1. Edit config.py with your bot token and chat IDs")
    print("2. Run: python manage_users.py (to add users)")
    print("3. Run: python test_bot.py (to test your bot)")
    print("4. Run: python reservation_checker.py (to test the checker)")
    
    print("\n🔒 Security notes:")
    print("- config.py is in .gitignore (won't be committed to git)")
    print("- Keep your bot token and chat IDs private")
    print("- Never share your config.py file")
    
    print("\n📖 For help:")
    print("- See README.md for detailed instructions")
    print("- Use manage_users.py to manage users easily")

if __name__ == "__main__":
    main() 
