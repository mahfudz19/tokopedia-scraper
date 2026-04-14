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
            print("[*] Tidak ada paginasi (Antarmuka Lazada mungkin menggunakan infinite scroll).")
            return active_page_number, next_url

        active_page_locator = pagination_locator.locator("li.ant-pagination-item-active")
        if await active_page_locator.is_visible():
            active_page_number = await active_page_locator.inner_text(timeout=3000)
            print(f"[*] Halaman yang saat ini aktif: {active_page_number}")

        next_button_locator = pagination_locator.locator("li.ant-pagination-next:not(.ant-pagination-disabled) a, button.ant-pagination-next")
        if await next_button_locator.is_visible():
            next_url = await next_button_locator.get_attribute("href")
            if next_url and not next_url.startswith("http"):
                next_url = "https://www.lazada.co.id" + next_url
            print(f"[+] Halaman berikutnya tersedia: {next_url}")
        else:
            print("[-] Ini adalah halaman terakhir.")

    except Exception as e:
        print(f"[-] Gagal mendeteksi informasi paginasi: {e}")

    return active_page_number, next_url


async def extract_data(page: Page, keyword: str) -> List[Dict[str, Any]]:
    """Mengekstrak data dari DOM Lazada berdasarkan data-qa-locator."""
    print(f"\n[*] Mengekstrak data produk Lazada untuk keyword: '{keyword}'...")

    extracted_data: List[Dict[str, Any]] = await page.evaluate(
        """(searchKeyword) => {
        const results = [];
        const cards = document.querySelectorAll('div[data-qa-locator="product-item"]');
        
        cards.forEach(card => {
            const aTag = card.querySelector('a');
            if (!aTag) return; 
            
            // 1. Identifikasi URL & ID (SANGAT URGENT)
            let raw_url = aTag.href;
            if (raw_url.startsWith('//')) {
                raw_url = 'https:' + raw_url;
            }
            const clean_url = raw_url.split('?')[0]; 
            
            // Mengambil ID Spesifik dari atribut data-item-id
            const marketplace_product_id = card.getAttribute('data-item-id') || clean_url;
            
            // 2. Ekstrak Image URL Mentah (SANGAT URGENT)
            const imgTag = card.querySelector('img[type="product"]') || card.querySelector('div.picture-wrapper img');
            const image_url_raw = imgTag ? (imgTag.src || imgTag.getAttribute('data-src')) : null;

            // Ambil semua node teks untuk diproses
            const textNodes = Array.from(card.querySelectorAll('*'))
                .filter(el => el.children.length === 0 && el.textContent.trim().length > 0)
                .map(el => el.textContent.trim());
            
            let title = "Nama tidak ditemukan";
            const titleLink = card.querySelector('a[title]');
            if (titleLink) {
                title = titleLink.getAttribute('title');
            }

            let prices = [];
            let discount_percent = 0;
            let rating = 0; 
            let sold_count = 0;
            let shop = "Lazada Seller"; 
            let location = "Lokasi tidak diketahui";
            
            // 3. Ekstrak DISKON (Mencari teks seperti '28% Off')
            const discountMatch = textNodes.find(t => t.match(/\\d+%\\s*(Off)?/i));
            if (discountMatch) {
                const num = discountMatch.match(/(\\d+)/);
                if(num) discount_percent = parseInt(num[0]) || 0;
            }

            // 4. Ekstrak HARGA
            const rpNodes = textNodes.filter(t => t.toLowerCase().startsWith("rp"));
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

            // 5. Ekstrak TERJUAL (Mencari '4.4K sold' atau 'terjual')
            const soldStr = textNodes.find(t => t.toLowerCase().includes("sold") || t.toLowerCase().includes("terjual"));
            if (soldStr) {
                let s = soldStr.toLowerCase().replace("sold", "").replace("terjual", "").replace(/\\+/g, "").trim();
                if (s.includes("k") || s.includes("rb")) {
                    sold_count = parseInt(parseFloat(s.replace("k", "").replace("rb", "").replace(",", ".")) * 1000);
                } else {
                    sold_count = parseInt(s) || 0;
                }
            }

            // 6. Ekstrak LOKASI (Kota/Kab)
            const locNode = textNodes.find(t => t.startsWith("Kota ") || t.startsWith("Kab. ") || t.startsWith("DKI "));
            if (locNode) {
                location = locNode;
            } else if (textNodes.length > 0) {
                const lastText = textNodes[textNodes.length - 1];
                if (!lastText.match(/^\\d/)) {
                    location = lastText;
                }
            }
            
            // Validasi & Simpan
            if (price_rp > 0 && title !== "Nama tidak ditemukan") {
                results.push({ 
                    search_keyword: searchKeyword,
                    category: [searchKeyword], // Standard Baru: Array of String
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
                    marketplace: "Lazada",
                });
            }
        });
        return results;
    }""", keyword
    )
    return extracted_data


async def scrape_lazada_tag(keyword: str, show_head: bool = False) -> None:
    mode_text = "HEADFUL (UI Terbuka)" if show_head else "HEADLESS (Background)"
    print(f"--- Membuka Browser Lazada [{mode_text}] ---")

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
        # Lazada biasanya menggunakan search?q= untuk pencarian global
        url = f"https://www.lazada.co.id/catalog/?q={formatted_keyword}"

        print(f"[*] Mencoba membuka: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # Mendeteksi Anti-Bot Lazada (Sering muncul saat scraping)
            if "baxia" in page.url or await page.locator("div#nocaptcha").is_visible():
                print("[!] Terdeteksi Anti-Bot Lazada! Coba jalankan dengan argument --head untuk bypass (solve geser puzzle manual).")
                await browser.close()
                return
                
        except Exception as e:
            print(f"[!] Halaman gagal dimuat (Timeout/Diblokir): {e}")
            await browser.close()
            return

        # 1. Scroll untuk load images
        pagination_locator = await scroll_to_bottom(page, max_attempts=15)

        # 2. Extract Pagination
        pagination_locator = page.locator("ul.ant-pagination")
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
                    if img_raw.startswith("//"):
                        img_raw = "https:" + img_raw
                        
                    s3_url = await asyncio.to_thread(upload_image_to_s3, img_raw)
                    
                    if s3_url:
                        # STANDARD BARU: Simpan hanya path S3-nya (Memotong domain amazonaws)
                        bucket_domain = "amazonaws.com/"
                        if bucket_domain in s3_url:
                            item["image_url"] = s3_url.split(bucket_domain)[1]
                        else:
                            item["image_url"] = s3_url
                            
                        upload_success += 1
                    else:
                        item["image_url"] = img_raw # Fallback ke raw jika S3 gagal
                        upload_failed += 1
                else:
                    item["image_url"] = None
                
                # Buang data mentah
                item.pop("image_url_raw", None)
                
                # STANDARD BARU: Hapus createdAt agar tidak bentrok dengan Upsert MongoDB
                item["updatedAt"] = datetime.now()

            print(f"[*] Status Upload S3: {upload_success} Gambar Berhasil, {upload_failed} Gambar Gagal.")

            # 5. Distribusikan Data
            db.insert_products(data, source_marketplace="Lazada")
        else:
            print("[-] Tidak ada data yang diekstrak. (Mungkin terhalang Anti-bot/Struktur berubah)")

        # 6. Backup Lokal
        await save_data_to_json(data, keyword, active_page_number, prefix="lazada")
        await save_page_as_mhtml(page, keyword, active_page_number, prefix="lazada")

        print("\n✓ Proses selesai. Browser ditutup dengan sukses.")
        await browser.close()