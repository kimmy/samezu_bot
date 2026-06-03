#!/usr/bin/env python3
"""
Test script to check slot detection logic
"""

import asyncio
import logging
from reservation_checker_playwright import ReservationChecker

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

async def test_slot_detection():
    """Test the slot detection logic"""
    print("🔍 Testing slot detection...")
    
    checker = ReservationChecker()
    
    try:
        # Run a check without notifications
        result = await checker.run_check(send_notifications=False)
        print(f"\n📊 RESULT:\n{result}")
        
        # Also test with month navigation
        print("\n🔍 Testing with month navigation...")
        result_month = await checker.run_check(send_notifications=False, use_month_navigation=True)
        print(f"\n📊 RESULT (month navigation):\n{result_month}")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_slot_detection()) 
