#!/usr/bin/env python3
"""
User Management Script for Tokyo Police Department Reservation Checker
Helps add, remove, and configure users for notifications.
"""

import json
import os
from typing import Dict, Any

CONFIG_FILE = "config.py"

def load_current_users() -> Dict[str, Any]:
    """Load current users from config.py"""
    try:
        # Read the config file
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract the TELEGRAM_USERS dictionary
        start = content.find("TELEGRAM_USERS = {")
        if start == -1:
            return {}
        
        # Find the end of the dictionary
        brace_count = 0
        end = start
        for i, char in enumerate(content[start:], start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        users_str = content[start:end]
        # Convert the string representation to actual dict
        users_str = users_str.replace("TELEGRAM_USERS = ", "")
        
        # Use eval to safely convert string to dict (since we control the format)
        return eval(users_str)
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users(users: Dict[str, Any]):
    """Save users back to config.py"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find and replace the TELEGRAM_USERS section
        start = content.find("TELEGRAM_USERS = {")
        if start == -1:
            print("Could not find TELEGRAM_USERS in config.py")
            return False
        
        # Find the end of the dictionary
        brace_count = 0
        end = start
        for i, char in enumerate(content[start:], start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        
        # Create the new users string
        users_str = "TELEGRAM_USERS = {\n"
        for chat_id, config in users.items():
            users_str += f'    "{chat_id}": {{\n'
            users_str += f'        "name": "{config["name"]}",\n'
            users_str += f'        "notify_no_slots": {config["notify_no_slots"]},\n'
            users_str += f'        "notify_slots": {config["notify_slots"]},\n'
            users_str += f'        "notify_errors": {config["notify_errors"]}\n'
            users_str += "    },\n"
        users_str += "}"
        
        # Replace the old section with the new one
        new_content = content[:start] + users_str + content[end:]
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False

def add_user(chat_id: str, name: str, notify_no_slots: bool = True, 
             notify_slots: bool = True, notify_errors: bool = True):
    """Add a new user"""
    users = load_current_users()
    
    users[chat_id] = {
        "name": name,
        "notify_no_slots": notify_no_slots,
        "notify_slots": notify_slots,
        "notify_errors": notify_errors
    }
    
    if save_users(users):
        print(f"✅ Added user {name} ({chat_id})")
        print(f"   - No slots notifications: {notify_no_slots}")
        print(f"   - Slot notifications: {notify_slots}")
        print(f"   - Error notifications: {notify_errors}")
    else:
        print("❌ Failed to add user")

def remove_user(chat_id: str):
    """Remove a user"""
    users = load_current_users()
    
    if chat_id in users:
        name = users[chat_id]["name"]
        del users[chat_id]
        
        if save_users(users):
            print(f"✅ Removed user {name} ({chat_id})")
        else:
            print("❌ Failed to remove user")
    else:
        print(f"❌ User {chat_id} not found")

def list_users():
    """List all users"""
    users = load_current_users()
    
    if not users:
        print("No users configured")
        return
    
    print("📋 Current users:")
    for chat_id, config in users.items():
        print(f"   {config['name']} ({chat_id})")
        print(f"      - No slots: {config['notify_no_slots']}")
        print(f"      - Slots: {config['notify_slots']}")
        print(f"      - Errors: {config['notify_errors']}")
        print()

def update_user_preferences(chat_id: str, notify_no_slots: bool = None, 
                          notify_slots: bool = None, notify_errors: bool = None):
    """Update user notification preferences"""
    users = load_current_users()
    
    if chat_id not in users:
        print(f"❌ User {chat_id} not found")
        return
    
    if notify_no_slots is not None:
        users[chat_id]["notify_no_slots"] = notify_no_slots
    if notify_slots is not None:
        users[chat_id]["notify_slots"] = notify_slots
    if notify_errors is not None:
        users[chat_id]["notify_errors"] = notify_errors
    
    if save_users(users):
        print(f"✅ Updated preferences for {users[chat_id]['name']} ({chat_id})")
    else:
        print("❌ Failed to update preferences")

def main():
    """Main function with interactive menu"""
    while True:
        print("\n🔧 User Management for Reservation Checker")
        print("1. List users")
        print("2. Add user")
        print("3. Remove user")
        print("4. Update user preferences")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            list_users()
        
        elif choice == "2":
            chat_id = input("Enter chat ID: ").strip()
            name = input("Enter user name: ").strip()
            
            notify_no_slots = input("Send 'no slots' messages? (y/n, default: y): ").strip().lower() != 'n'
            notify_slots = input("Send slot notifications? (y/n, default: y): ").strip().lower() != 'n'
            notify_errors = input("Send error notifications? (y/n, default: y): ").strip().lower() != 'n'
            
            add_user(chat_id, name, notify_no_slots, notify_slots, notify_errors)
        
        elif choice == "3":
            chat_id = input("Enter chat ID to remove: ").strip()
            remove_user(chat_id)
        
        elif choice == "4":
            chat_id = input("Enter chat ID: ").strip()
            users = load_current_users()
            
            if chat_id not in users:
                print(f"❌ User {chat_id} not found")
                continue
            
            print(f"Current preferences for {users[chat_id]['name']}:")
            print(f"  - No slots: {users[chat_id]['notify_no_slots']}")
            print(f"  - Slots: {users[chat_id]['notify_slots']}")
            print(f"  - Errors: {users[chat_id]['notify_errors']}")
            
            notify_no_slots = input("Send 'no slots' messages? (y/n, leave empty to keep current): ").strip().lower()
            notify_slots = input("Send slot notifications? (y/n, leave empty to keep current): ").strip().lower()
            notify_errors = input("Send error notifications? (y/n, leave empty to keep current): ").strip().lower()
            
            no_slots = None if notify_no_slots == "" else notify_no_slots == 'y'
            slots = None if notify_slots == "" else notify_slots == 'y'
            errors = None if notify_errors == "" else notify_errors == 'y'
            
            update_user_preferences(chat_id, no_slots, slots, errors)
        
        elif choice == "5":
            print("👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main() 