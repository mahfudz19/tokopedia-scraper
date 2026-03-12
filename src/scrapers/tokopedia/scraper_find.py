from typing import Tuple, Optional, List, Dict, Any
from playwright.async_api import async_playwright, Page, Locator

from src.utils import save_page_as_mhtml, scroll_to_bottom, save_data_to_json
from src.database import db


async def extract_pagination_info(
    pagination_locator: Locator,
) -> Tuple[str, Optional[str]]:
    active_page_number: str = "1"
    next_url: Optional[str] = None

    try:
        if await pagination_locator.count() == 0:
            print("[*] Tidak ada paginasi. Ini adalah satu-satunya halaman.")
            return active_page_number, next_url

        active_page_locator = pagination_locator.locator(
            "a[data-active='true'], span[data-active='true']"
        )
        active_page_number = await active_page_locator.inner_text(timeout=3000)
        print(f"[*] Halaman yang saat ini aktif: {active_page_number}")

        next_button_locator = pagination_locator.locator(
            "a[aria-label='Laman berikutnya'], button[aria-label='Laman berikutnya']"
        )
        if await next_button_locator.is_visible():
            next_url = await next_button_locator.get_attribute("href")
            print(f"[+] Halaman berikutnya tersedia: {next_url}")
        else:
            print("[-] Ini adalah halaman terakhir.")

    except Exception as e:
        print(f"[-] Gagal mendeteksi informasi paginasi: {e}")

    return active_page_number, next_url


async def extract_data(page: Page) -> List[Dict[str, Any]]:
    """Hanya bertugas mengekstrak data dari DOM, tanpa melakukan penyimpanan."""
    print("\n[*] Mengekstrak data produk...")

    extracted_data: List[Dict[str, Any]] = await page.evaluate(
        """() => {
        const results = [];
        const cards = document.querySelectorAll('div[data-testid^="divFindProduct"]');
        
        cards.forEach(card => {
            const aTag = card.querySelector('a');
            if (!aTag) return; 
            
            // CLEANING URL: Buang semua parameter tracking setelah tanda '?'
            const url = aTag.href.split('?')[0];
            
            const texts = aTag.innerText.split('\\n').map(t => t.trim()).filter(t => t.length > 0);
            
            let title = "Nama tidak ditemukan";
            let price = 0;
            let shop = "Toko tidak diketahui";
            let location = "Lokasi tidak diketahui";
            
            for (let i = 0; i < texts.length; i++) {
                const text = texts[i];
                if (text.startsWith("Rp") && price === 0) {
                    price = parseInt(text.replace(/[^0-9]/g, '')) || 0;
                } else if (text.length > 15 && title === "Nama tidak ditemukan" && price === 0) {
                    title = text;
                }
            }
            
            if (texts.length >= 2) {
                location = texts[texts.length - 1]; 
                shop = texts[texts.length - 2];     
            }
            
            if (price > 0 && title !== "Nama tidak ditemukan") {
                results.push({ name: title, price_rp: price, shop: shop, location: location, url: url });
            }
        });
        return results;
    }"""
    )
    return extracted_data


async def scrape_find_page(keyword: str) -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        formatted_keyword = keyword.replace(" ", "%20").lower()
        url = f"https://www.tokopedia.com/find/{formatted_keyword}?utm_source=google&utm_medium=organic&utm_campaign=find&page=1"

        print(f"[*] Mencoba membuka: {url}")

        # 3. BUNGKUS DENGAN TRY-EXCEPT DAN TAMBAHKAN TIMEOUT (60 Detik)
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[!] Halaman gagal dimuat (Timeout/Diblokir): {e}")
            await browser.close()
            return  # Langsung keluar dari fungsi ini tanpa error merah di terminal

        # 1. Scroll
        pagination_locator = await scroll_to_bottom(page, max_attempts=15)

        # 2. Extract Pagination
        active_page_number, next_url = await extract_pagination_info(pagination_locator)

        # 3. Extract Data Mentah
        data: List[Dict[str, Any]] = await extract_data(page)

        # 4. Distribusikan Data (JSON Lokal & MongoDB)
        if data:
            db.insert_products(data, source_marketplace="Tokopedia")
        else:
            print("[-] Tidak ada data yang diekstrak.")

        # 5. Backup HTML
        await save_data_to_json(data, keyword, active_page_number)
        await save_page_as_mhtml(page, keyword, active_page_number)

        print("\n✓ Proses selesai. Browser ditutup dengan sukses.")
        await browser.close()
