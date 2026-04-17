import asyncio
from datetime import datetime
from typing import Tuple, Optional, List, Dict, Any
from playwright.async_api import async_playwright, Page, Locator

from src.utils import save_page_as_mhtml, scroll_to_bottom, save_data_to_json, upload_image_to_s3
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


async def extract_data(page: Page, keyword: str) -> List[Dict[str, Any]]:
    """Mengekstrak data komprehensif dari DOM Tokopedia versi terbaru."""
    print(f"\n[*] Mengekstrak data produk untuk keyword: '{keyword}'...")

    extracted_data: List[Dict[str, Any]] = await page.evaluate(
        r"""(searchKeyword) => {
        const results = [];
        
        // 1. Cari Container Utama yang stabil (data-testid jarang berubah)
        const container = document.querySelector('div[data-testid="divSRPContentProducts"]');
        if (!container) return results;

        // 2. Ambil semua link produk di dalamnya
        const cards = container.querySelectorAll('a[href]');
        
        cards.forEach(aTag => {
            const raw_url = aTag.href;
            // Pastikan ini adalah link produk, bukan link promo/iklan banner
            if (!raw_url || !raw_url.includes('tokopedia.com/')) return;
            if (raw_url.includes('/promo') || raw_url.includes('/discovery')) return; 
            
            const clean_url = raw_url.split('?')[0]; 
            const marketplace_product_id = clean_url; 
            
            // 3. Ekstrak Image URL
            let image_url_raw = null;
            // Mencari gambar dengan alt "product-image" (Sangat stabil)
            const imgTag = aTag.querySelector('img[alt="product-image"]');
            if (imgTag) {
                let src = imgTag.src || imgTag.getAttribute('data-src') || imgTag.getAttribute('srcset')?.split(' ')[0];
                // Tokopedia menggunakan svg zeus_v2 sebagai placeholder lazy-load. Abaikan jika belum terload.
                if (src && !src.includes('zeus_v2')) {
                    image_url_raw = src;
                }
            }

            // 4. Kumpulkan Text Nodes untuk Heuristik
            const textNodes = Array.from(aTag.querySelectorAll('*'))
                .filter(el => el.children.length === 0 && el.textContent.trim().length > 0)
                .map(el => el.textContent.trim());
            
            let title = "Nama tidak ditemukan";
            let prices = [];
            let discount_percent = 0;
            let rating = 0;
            let sold_count = 0;
            let shop = "Toko tidak diketahui";
            let location = "Lokasi tidak diketahui";
            
            // Ekstrak DISKON
            const discountMatch = textNodes.find(t => t.match(/^\d+%$/));
            if (discountMatch) {
                discount_percent = parseInt(discountMatch.replace('%', '')) || 0;
            }

            // Ekstrak HARGA
            const rpNodes = textNodes.filter(t => t.startsWith("Rp"));
            rpNodes.forEach(rp => {
                const num = parseInt(rp.replace(/[^0-9]/g, ''));
                if (num && num > 0) prices.push(num);
            });
            
            let price_rp = 0;
            let price_original = 0;
            if (prices.length > 0) {
                price_original = Math.max(...prices); 
                price_rp = Math.min(...prices);       
            }

            // Ekstrak NAMA PRODUK
            // Logika: Teks yang panjangnya lumayan, bukan harga, bukan jumlah terjual, dll.
            const potentialTitles = textNodes.filter(t => 
                t.length > 10 && 
                !t.startsWith("Rp") && 
                !t.toLowerCase().includes("terjual") && 
                !t.toLowerCase().includes("hemat") && 
                !t.toLowerCase().includes("cashback") && 
                !t.match(/^[0-5]\.[0-9]$/)
            );
            if (potentialTitles.length > 0) {
                title = potentialTitles[0];
            }

            // Ekstrak RATING
            const ratingStr = textNodes.find(t => t.match(/^[0-5]\.[0-9]$/));
            if(ratingStr) rating = parseFloat(ratingStr) || 0;

            // Ekstrak TERJUAL
            const soldStr = textNodes.find(t => t.toLowerCase().includes("terjual"));
            if (soldStr) {
                let s = soldStr.toLowerCase().replace("terjual", "").replace(/\+/g, "").trim();
                if (s.includes("rb")) {
                    sold_count = parseInt(parseFloat(s.replace("rb", "").replace(",", ".")) * 1000);
                } else if (s.includes("jt")) {
                    sold_count = parseInt(parseFloat(s.replace("jt", "").replace(",", ".")) * 1000000);
                } else {
                    sold_count = parseInt(s) || 0;
                }
            }

            // Ekstrak TOKO & LOKASI
            // Tokopedia versi ini sering menaruh nama toko dan lokasi dengan class yg ada kata "flip"
            const flipNodes = Array.from(aTag.querySelectorAll('span[class*="flip"]')).map(el => el.textContent.trim());
            if (flipNodes.length >= 2) {
                shop = flipNodes[0];
                location = flipNodes[1];
            } else if (flipNodes.length === 1) {
                shop = flipNodes[0];
            } else {
                // Fallback Heuristik (Tebak dari posisi teks)
                const locationCandidates = textNodes.filter(t => !t.startsWith("Rp") && !t.includes("terjual") && !t.includes("%") && t.length < 25);
                if (locationCandidates.length >= 2) {
                    location = locationCandidates[locationCandidates.length - 1];
                    shop = locationCandidates[locationCandidates.length - 2];     
                }
            }
            
            // Validasi & Simpan ke Array
            if (price_rp > 0 && title !== "Nama tidak ditemukan" && shop !== "Toko tidak diketahui") {
                results.push({ 
                    search_keyword: searchKeyword,
                    category: [searchKeyword],
                    marketplace_product_id: marketplace_product_id,
                    clean_url: clean_url,
                    url: clean_url, 
                    name: title, 
                    price_original: price_original,
                    price_rp: price_rp, 
                    discount_percent: discount_percent,
                    rating: rating,
                    sold_count: sold_count,
                    shop: shop, 
                    location: location, 
                    image_url_raw: image_url_raw, 
                    marketplace: "Tokopedia",
                });
            }
        });
        return results;
    }""", keyword
    )
    return extracted_data

async def scrape_find_page(keyword: str, show_head: bool = False) -> None:
    mode_text = "HEADFUL (UI Terbuka)" if show_head else "HEADLESS (Background)"
    print(f"--- Membuka Browser Tokopedia [{mode_text}] ---")

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

        print(f"[*] Mencoba membuka: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[!] Halaman gagal dimuat (Timeout/Diblokir): {e}")
            await browser.close()
            return

        # 1. Scroll untuk load images & data
        await scroll_to_bottom(page, max_attempts=15)

        # 2. Extract Pagination
        pagination_locator = page.locator("nav[aria-label='Laman navigasi'], div[data-testid='divSRPPagination']")
        active_page_number, next_url = await extract_pagination_info(pagination_locator)
        
        # 3. Extract Data Mentah
        data: List[Dict[str, Any]] = await extract_data(page, keyword)

        if data:
            print(f"[*] Memproses {len(data)} produk untuk S3 Upload & Formatting...")
            
            # 4. Upload Gambar ke AWS S3
            upload_success = 0
            upload_failed = 0

            for item in data:
                img_raw = item.get("image_url_raw")
                if img_raw:
                    s3_url = await asyncio.to_thread(upload_image_to_s3, img_raw)
                    
                    if s3_url:
                        item["image_url"] = s3_url
                        upload_success += 1
                    else:
                        item["image_url"] = img_raw 
                        upload_failed += 1
                else:
                    item["image_url"] = None
                
                item.pop("image_url_raw", None)
                item["updatedAt"] = datetime.now()

            print(f"[*] Status Upload S3: {upload_success} Gambar Berhasil, {upload_failed} Gambar Gagal.")

            # 5. Distribusikan Data ke DB
            db.insert_products(data, source_marketplace="Tokopedia")
        else:
            print("[-] Tidak ada data yang diekstrak. Format Tokopedia mungkin berubah drastis.")

        await save_data_to_json(data, keyword, active_page_number)
        await save_page_as_mhtml(page, keyword, active_page_number)

        print("\n✓ Proses selesai. Browser ditutup dengan sukses.")
        await browser.close()