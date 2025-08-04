#!/usr/bin/env python3
"""
Debug script to examine the table structure and extract dates correctly
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_table():
    """Debug the table structure to understand date extraction."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # Show browser for debugging
        context = await browser.new_context()
        page = await context.new_page()
        
        # Navigate to the target URL
        url = "https://www.keishicho-gto.metro.tokyo.lg.jp/keishicho-u/reserve/offerList_detail?tempSeq=445&accessFrom=offerList"
        await page.goto(url, timeout=30000)
        
        # Wait for page to load
        await page.wait_for_selector('table', timeout=30000)
        await page.wait_for_timeout(2000)
        
        print("🔍 Examining table structure...")
        
        # Get all headers
        headers = await page.query_selector_all('th')
        print(f"📋 Found {len(headers)} headers:")
        for i, header in enumerate(headers):
            text = await header.text_content()
            print(f"   Header {i}: '{text}'")
        
        # Get all table rows
        rows = await page.query_selector_all('tr')
        print(f"\n📊 Found {len(rows)} rows:")
        
        for i, row in enumerate(rows[:3]):  # Show first 3 rows
            cells = await row.query_selector_all('td')
            print(f"   Row {i}: {len(cells)} cells")
            for j, cell in enumerate(cells):
                text = await cell.text_content()
                print(f"     Cell {j}: '{text}'")
        
        # Try different selectors for date headers
        print("\n🔍 Trying different date header selectors:")
        
        # Method 1: All th elements
        all_headers = await page.query_selector_all('th')
        print(f"   All headers: {len(all_headers)}")
        
        # Method 2: Skip first two columns
        date_headers = await page.query_selector_all('th:nth-child(n+3)')
        print(f"   Date headers (n+3): {len(date_headers)}")
        
        # Method 3: Direct nth-child selectors
        for i in range(3, 10):  # Check columns 3-9
            try:
                header = await page.query_selector(f'th:nth-child({i})')
                if header:
                    text = await header.text_content()
                    print(f"   Header {i}: '{text}'")
            except:
                pass
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_table()) 
