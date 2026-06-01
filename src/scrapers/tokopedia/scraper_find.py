import asyncio
import time
from datetime import datetime, timezone
from typing import Tuple, Optional, List, Dict, Any
from playwright.async_api import async_playwright, Page, Locator

from src.database import db

async def extract_data(page: Page, keyword: str) -> List[Dict[str, Any]]:
    """Ekstrak data produk Tokopedia dengan textNodes approach."""
    print(f"\n[*] Mengekstrak data produk untuk keyword: '{keyword}'...")

    extracted_data: List[Dict[str, Any]] = await page.evaluate(
        r"""(searchKeyword) => {
        const results = [];
        const container = document.querySelector('div[data-testid="divSRPContentProducts"]');
        if (!container) return results;

        const cards = container.querySelectorAll('a[href]');

        cards.forEach(aTag => {
            const raw_url = aTag.href;
            // Early exit: filter link produk
            if (!raw_url || !raw_url.includes('tokopedia.com/')) return;
            if (raw_url.includes('/promo') || raw_url.includes('/discovery')) return;

            const url = raw_url.split('?')[0];

            // 1. NAMA PRODUK - textNodes approach (proven to work)
            let name = "Nama tidak ditemukan";
            const textNodes = Array.from(aTag.querySelectorAll('*'))
                .filter(el => el.children.length === 0 && el.textContent.trim().length > 0)
                .map(el => el.textContent.trim());

            // Cari nama: text panjang (>15 chars) yang bukan harga/lokasi
            for (const text of textNodes) {
                if (text.length > 15 && text.length < 100 && !text.includes('Rp') && !text.includes('terjual')) {
                    name = text;
                    break;
                }
            }

            // 2. HARGA - parse dari textNodes
            let price_rp = 0;
            const fullText = aTag.textContent;
            const priceMatch = fullText.match(/Rp(\d{1,3}(?:[.\d{3}]*))/);
            if (priceMatch) {
                price_rp = parseInt(priceMatch[1].replace(/\./g, ''));
            }

            // 3. LOKASI & TOKO - dari span[class*="flip"] (sudah optimal)
            let location = "Lokasi tidak diketahui";
            let shop = "Toko tidak diketahui";

            const flipNodes = Array.from(aTag.querySelectorAll('span[class*="flip"]')).map(el => el.textContent.trim());
            if (flipNodes.length >= 2) {
                shop = flipNodes[0];
                location = flipNodes[1];
            } else if (flipNodes.length === 1) {
                shop = flipNodes[0];
            }

            // Validasi & Simpan
            if (price_rp > 0 && name !== "Nama tidak ditemukan") {
                results.push({ url, name, price_rp, shop, location });
            }
        });
        return results;
    }""", keyword
    )
    print(f"    [✓] Berhasil mengekstrak {len(extracted_data)} produk")
    return extracted_data

async def scroll_to_bottom_tokopedia(page: Page, max_attempts: int = 35, scroll_multiplier: float = 1.5, wait_for_timeout=500) -> None:
    """Scroll to bottom dengan viewport-based approach untuk Tokopedia.

    Menggunakan scroll agresif (1.5x viewport) untuk trigger lazy-load.
    Sweet spot: cepat tapi tetap dapat banyak produk (~50-80).
    """
    print(f"\n[*] Memulai auto-scroll Tokopedia (max_attempts={max_attempts}, {scroll_multiplier}x viewport)...")
    attempts: int = 0
    consecutive_no_growth: int = 0
    max_consecutive_no_growth: int = 3

    last_scroll_position: float = await page.evaluate("window.scrollY")
    last_content_height: float = await page.evaluate("(document.body || document.documentElement).scrollHeight")

    while attempts < max_attempts:
        # Scroll 1.5x viewport height - sweet spot untuk trigger lazy-load
        scroll_distance: float = await page.evaluate(f"window.innerHeight * {scroll_multiplier}")
        await page.evaluate(f"window.scrollBy(0, {scroll_distance})")

        # Wait untuk lazy-load produk
        await page.wait_for_timeout(wait_for_timeout)

        new_scroll_position: float = await page.evaluate("window.scrollY")
        new_content_height: float = await page.evaluate("(document.body || document.documentElement).scrollHeight")

        content_grew = new_content_height > last_content_height
        scroll_worked = new_scroll_position > last_scroll_position

        # Debug progress setiap 10 scroll
        if attempts % 10 == 0 and attempts > 0:
            print(f"    [debug] Scroll #{attempts}: height={new_content_height:.0f}px")

        if not scroll_worked:
            print("[✓] Scroll selesai: sudah mentok bawah.")
            break

        if not content_grew:
            consecutive_no_growth += 1
            if consecutive_no_growth >= max_consecutive_no_growth:
                print("[✓] Scroll selesai: content tidak bertambah.")
                break
        else:
            consecutive_no_growth = 0

        last_scroll_position = new_scroll_position
        last_content_height = new_content_height
        attempts += 1

    print(f"    [✓] Scroll selesai: {attempts} attempts, final height={last_content_height:.0f}px")
    if attempts == max_attempts:
        print("[!] Scroll berhenti: mencapai batas maksimal percobaan.")


async def scrape_find_page(keyword: str, show_head: bool = False) -> Dict[str, Any]:
    """Scrape produk Tokopedia berdasarkan keyword dan simpan ke database.

    Returns:
        Dict dengan keys: success, keyword, products_count, db_new, db_updated, duration, error
    """
    start_time = time.time()
    mode_text = "HEADFUL (UI Terbuka)" if show_head else "HEADLESS (Background)"

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=not show_head,
                channel="chrome",
                ignore_default_args=["--enable-automation"],
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()

            formatted_keyword = keyword.replace(" ", "%20").lower()
            url = f"https://www.tokopedia.com/search?navsource=home&q={formatted_keyword}&source=universe&st=product&page=1"

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                await browser.close()
                raise e

            # 1. Scroll untuk load images & data
            await scroll_to_bottom_tokopedia(page, max_attempts=35, scroll_multiplier=1.5, wait_for_timeout=500)

            # 2. Extract Data Mentah
            data: List[Dict[str, Any]] = await extract_data(page, keyword)

            # 3. Simpan ke Database dan dapatkan stats
            db_new = 0
            db_updated = 0

            if data:
                result = db.insert_products(data, source_marketplace="Tokopedia", search_keyword=keyword)
                if result:
                    db_new = result.get("new", 0)
                    db_updated = result.get("updated", 0)

            await browser.close()

            duration = time.time() - start_time

            return {
                "success": True,
                "keyword": keyword,
                "products_count": len(data),
                "db_new": db_new,
                "db_updated": db_updated,
                "duration": duration,
                "error": None
            }

    except Exception as e:
        duration = time.time() - start_time
        return {
            "success": False,
            "keyword": keyword,
            "products_count": 0,
            "db_new": 0,
            "db_updated": 0,
            "duration": duration,
            "error": str(e)[:100]
        }
