import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth # Menggunakan versi stealth terbaru
from src.utils import save_page_as_mhtml, scroll_to_element # Menggunakan alat bantu

async def scrape_search_page(keyword):
    """
    Eksperimental: Scraping melalui rute utama /search.
    Risiko terkena blokir (403/CAPTCHA) sangat tinggi.
    """
    print("--- EKSPERIMEN: Metode /search ---")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Penyamaran bot
        await stealth(page)
        
        # URL diperbaiki agar benar-benar mengarah ke rute pencarian utama
        url = f"https://www.tokopedia.com/search?q={keyword}"
        print(f"[*] Mencoba mengakses: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded")
            
            # Kita bisa menggunakan fungsi scroll dari utils.py
            # Namun selectornya mungkin berbeda, jadi kita coba scroll biasa dulu
            tinggi_layar = await page.evaluate("window.innerHeight")
            await page.mouse.wheel(0, tinggi_layar)
            await page.wait_for_timeout(3000)
            
            print("[?] Coba periksa browser, apakah kamu diblokir atau dimintai CAPTCHA?")
            
            # Menyimpan halaman sebagai bukti
            await save_page_as_mhtml(page, f"{keyword}_search_experiment", 1)
            
        except Exception as e:
            print(f"[!] Gagal mengakses: {e}")
            
        await browser.close()