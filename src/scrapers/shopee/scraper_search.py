import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Kita buang playwright_stealth sepenuhnya!

load_dotenv()

async def scrape_shopee_search(keyword: str) -> None:
    print("--- Step 1: Membuka Browser & Proses Login Shopee ---")

    async with async_playwright() as p:
        # Hanya gunakan argumen bawaan ini untuk menyembunyikan flag "WebDriver"
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome", 
            args=["--disable-blink-features=AutomationControlled"],
        )
        
        # Kita biarkan Playwright menggunakan User-Agent aslinya sendiri
        context = await browser.new_context()

        print("[*] Mengatur bahasa default ke Indonesia (id)...")
        await context.add_cookies([
            {
                "name": "language",
                "value": "id",
                "domain": ".shopee.co.id",
                "path": "/"
            }
        ])

        page = await context.new_page()

        print("[*] Membuka halaman login Shopee...")
        await page.goto("https://shopee.co.id/buyer/login", wait_until="domcontentloaded")

        shopee_user = os.getenv("SHOPEE_USER")
        shopee_pass = os.getenv("SHOPEE_PASS")

        if not shopee_user or not shopee_pass:
            print("[!] Error: Kredensial Shopee tidak ditemukan di .env!")
            return

        print("[*] Menunggu kolom input...")
        await page.wait_for_selector('input[name="loginKey"]')
        await asyncio.sleep(2) 
        
        print("[*] Mengetikkan username...")
        await page.locator('input[name="loginKey"]').click()
        await page.locator('input[name="loginKey"]').press_sequentially(shopee_user, delay=150)
        
        await asyncio.sleep(1)
        
        print("[*] Mengetikkan password...")
        await page.locator('input[name="password"]').click()
        await page.locator('input[name="password"]').press_sequentially(shopee_pass, delay=100)
        
        await asyncio.sleep(1)

        print("[*] Klik tombol Log In...")
        await page.click('button:has-text("Log In")')

        print("\n" + "="*50)
        print("[!] PERHATIAN: JIKA MUNCUL PUZZLE CAPTCHA,")
        print("    SILAKAN GESER SECARA MANUAL DI BROWSER.")
        print("    (Bot sedang menunggu selama 2 menit...)")
        print("="*50 + "\n")

        try:
            await page.wait_for_selector('input.shopee-searchbar-input__input', timeout=120000)
            print("[✓] Pintu berhasil ditembus! Anda berstatus Login.")
        except Exception as e:
            print("[-] Gagal login atau waktu habis. Error:", e)
            await browser.close()
            return

        formatted_keyword = keyword.replace(" ", "%20")
        url = f"https://shopee.co.id/search?keyword={formatted_keyword}"
        
        print(f"\n[*] Mengarahkan ke halaman pencarian: {url}")
        await page.goto(url, wait_until="domcontentloaded")

        print("[✓] Selesai! Halaman terbuka dengan status akun login.")
        print("[i] Browser akan dibiarkan terbuka selama 5 menit agar bisa Anda pantau.")
        
        await asyncio.sleep(300) 
        await browser.close()