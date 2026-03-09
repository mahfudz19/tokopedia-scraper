import asyncio
import argparse
import os
from playwright.async_api import async_playwright
from src.utils import save_page_as_mhtml, scroll_to_element
from src.database import db

# from playwright_stealth import Stealth


async def extract_pagination_info(pagination_locator):
    """
    Fungsi untuk mengekstrak nomor halaman yang sedang aktif
    dan mengecek apakah ada halaman selanjutnya.
    """
    active_page_number = "1"  # Default adalah halaman 1
    next_url = None

    try:
        # CEK DULU: Apakah elemen paginasi ada di dalam DOM?
        if await pagination_locator.count() == 0:
            print("[*] Tidak ada paginasi. Ini adalah satu-satunya halaman.")
            return active_page_number, next_url

        # Ekstrak halaman aktif
        active_page_locator = pagination_locator.locator(
            "a[data-active='true'], span[data-active='true']"
        )

        # Tambahkan timeout 3 detik agar tidak menunggu 30 detik jika ada error minor
        active_page_number = await active_page_locator.inner_text(timeout=3000)
        print(
            f"[*] Halaman yang saat ini aktif/terlihat adalah Halaman: {active_page_number}"
        )

        # Ekstrak halaman berikutnya
        next_button_locator = pagination_locator.locator(
            "a[aria-label='Laman berikutnya'], button[aria-label='Laman berikutnya']"
        )
        is_next_available = await next_button_locator.is_visible()

        if is_next_available:
            next_url = await next_button_locator.get_attribute("href")
            print(f"[+] Halaman berikutnya tersedia.")
            print(f"[*] URL Selanjutnya: {next_url}")
        else:
            print("[-] Ini adalah halaman terakhir. Tidak ada halaman berikutnya.")

    except Exception as e:
        print(f"[-] Gagal mendeteksi informasi paginasi: {e}")

    return active_page_number, next_url


async def extract_and_save_data(page, keyword, page_number):
    """
    Fungsi untuk mengekstrak data dari DOM HTML dan langsung menyimpannya ke MongoDB.
    """
    print("\n[*] Mengekstrak data produk...")

    # Kita menggunakan page.evaluate() untuk menjalankan JavaScript langsung di browser.
    extracted_data = await page.evaluate(
        """() => {
        const results = [];
        const cards = document.querySelectorAll('div[data-testid^="divFindProduct"]');
        
        cards.forEach(card => {
            const aTag = card.querySelector('a');
            if (!aTag) return; 
            
            const url = aTag.href;
            const texts = aTag.innerText.split('\\n').map(t => t.trim()).filter(t => t.length > 0);
            
            let title = "Nama tidak ditemukan";
            let price = 0;
            let shop = "Toko tidak diketahui";
            let location = "Lokasi tidak diketahui";
            
            for (let i = 0; i < texts.length; i++) {
                const text = texts[i];
                if (text.startsWith("Rp") && price === 0) {
                    price = parseInt(text.replace(/[^0-9]/g, '')) || 0;
                } 
                else if (text.length > 15 && title === "Nama tidak ditemukan" && price === 0) {
                    title = text;
                }
            }
            
            if (texts.length >= 2) {
                location = texts[texts.length - 1]; 
                shop = texts[texts.length - 2];     
            }
            
            if (price > 0 && title !== "Nama tidak ditemukan") {
                results.push({
                    name: title,
                    price_rp: price,
                    shop: shop,
                    location: location,
                    url: url
                });
            }
        });
        return results;
    }"""
    )

    if extracted_data:
        print(f"[*] Menemukan {len(extracted_data)} produk. Mengirim ke MongoDB...")
        db.insert_products(extracted_data, source_marketplace="Tokopedia")
    else:
        print("[-] Tidak ada data produk yang berhasil diekstrak.")


async def scrape_find_page(keyword):
    """
    Fungsi utama (Orchestrator) untuk mengatur alur kerja web scraping.
    """
    print("--- Step 1: Membuka Browser ---")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # stealth_plugin = Stealth()
        # await stealth_plugin.apply_stealth_async(page)

        formatted_keyword = keyword.replace(" ", "%20")
        url = f"https://www.tokopedia.com/find/{formatted_keyword}?utm_source=google&utm_medium=organic&utm_campaign=find&page=1"
        print(f"[*] Mencoba membuka: {url}")
        await page.goto(url, wait_until="domcontentloaded")

        pagination_locator = await scroll_to_element(
            page, "div[data-testid='cntrPagination']"
        )

        active_page_number, next_url = await extract_pagination_info(pagination_locator)

        await extract_and_save_data(page, keyword, active_page_number)

        await save_page_as_mhtml(page, keyword, active_page_number)

        print("\n✓ Proses selesai. Browser ditutup dengan sukses.")
        await browser.close()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Tokopedia Product Scraper")
    parser.add_argument(
        "--product",
        "-p",
        type=str,
        required=True,
        help="Product keyword to search (can contain spaces)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    asyncio.run(scrape_find_page(args.product))
