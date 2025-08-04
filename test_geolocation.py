#!/usr/bin/env python3
"""
Test script to simulate Railway's environment locally
"""

import asyncio
import time
from playwright.async_api import async_playwright

async def test_with_railway_headers():
    """Test with Railway-like headers (Singapore location)"""
    print("🔍 Testing with Railway-like headers (Singapore)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale='en-US',  # Singapore-like locale
            timezone_id='Asia/Singapore'
        )
        
        page = await context.new_page()
        
        # Set headers like Railway (Singapore)
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'X-Forwarded-For': '103.1.2.3',  # Singapore IP
            'CF-IPCountry': 'SG',  # Singapore
            'X-Real-IP': '103.1.2.3'
        })
        
        url = "https://www.keishicho-gto.metro.tokyo.lg.jp/keishicho-u/reserve/offerList_detail?tempSeq=445&accessFrom=offerList"
        
        try:
            await page.goto(url, timeout=30000)
            title = await page.title()
            current_url = page.url
            print(f"📄 Page title: {title}")
            print(f"🔗 Current URL: {current_url}")
            
            if "e-TUMO" in title:
                print("❌ Got e-TUMO page (Railway-like behavior)")
            else:
                print("✅ Got normal page")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await browser.close()

async def test_with_japanese_headers():
    """Test with Japanese headers"""
    print("\n🔍 Testing with Japanese headers...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            locale='ja-JP',
            timezone_id='Asia/Tokyo'
        )
        
        page = await context.new_page()
        
        # Set headers like Japanese user
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja-JP,ja;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'X-Forwarded-For': '203.0.113.1',  # Japanese IP
            'CF-IPCountry': 'JP',  # Japan
            'X-Real-IP': '203.0.113.1'
        })
        
        url = "https://www.keishicho-gto.metro.tokyo.lg.jp/keishicho-u/reserve/offerList_detail?tempSeq=445&accessFrom=offerList"
        
        try:
            await page.goto(url, timeout=30000)
            title = await page.title()
            current_url = page.url
            print(f"📄 Page title: {title}")
            print(f"🔗 Current URL: {current_url}")
            
            if "e-TUMO" in title:
                print("❌ Still got e-TUMO page")
            else:
                print("✅ Got normal page")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        await browser.close()

async def main():
    await test_with_railway_headers()
    await test_with_japanese_headers()

if __name__ == "__main__":
    asyncio.run(main()) 
