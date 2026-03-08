import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def scrape_search_page(keyword):
    """
    Eksperimental: Scraping melalui rute utama /search.
    Risiko terkena blokir (403/CAPTCHA) sangat tinggi.
    """
    url = f"https://www.tokopedia.com/find/{keyword}?utm_source=google&amp;utm_medium=organic&amp;utm_campaign=find&page=1"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await stealth_async(page)
        
        print(f"[*] [EKSPERIMEN] Mengakses halaman /search untuk: {keyword}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
            print("[?] Coba periksa browser, apakah kamu diblokir atau dimintai CAPTCHA?")
        except Exception as e:
            print(f"[!] Gagal mengakses: {e}")
            
        await browser.close()