from typing import  List, Dict, Any
from playwright.async_api import async_playwright, Page

from src.database import db

async def extract_data(page: Page, keyword: str) -> List[Dict[str, Any]]:
    """Mengekstrak data dari DOM Lazada berdasarkan data-qa-locator."""
    print(f"\n[*] Mengekstrak data produk Lazada untuk keyword: '{keyword}'...")

    extracted_data: List[Dict[str, Any]] = await page.evaluate(
        """
        (searchKeyword) => {
            const results = [];
            const cards = document.querySelectorAll('div[data-qa-locator="product-item"]');

            // Helper: parse sold count (handle "4.4K", "1.2rb", "77", dll)
            function parseSoldCount(text) {
                if (!text) return 0;
                let s = text.toLowerCase().replace(/sold|terjual/g, '').replace(/\\+/g, '').trim();
                if (s.includes('k') || s.includes('rb')) {
                    return parseInt(parseFloat(s.replace('k', '').replace('rb', '').replace(',', '.')) * 1000);
                }
                return parseInt(s) || 0;
            }

            cards.forEach(card => {
                const aTag = card.querySelector('a');
                if (!aTag) return;

                // 1. Identifikasi URL & ID
                let raw_url = aTag.href;
                if (raw_url.startsWith('//')) {
                    raw_url = 'https:' + raw_url;
                }
                const clean_url = raw_url.split('?')[0];
                const marketplace_product_id = card.getAttribute('data-item-id') || clean_url;

                // 2. Ekstrak Image URL
                const imgTag = card.querySelector('img[type="product"]') || card.querySelector('div.picture-wrapper img');
                const image_url_raw = imgTag ? (imgTag.src || imgTag.getAttribute('data-src')) : null;

                // 3. Ekstrak TITLE - Prioritas: img[alt] → a[title]
                let title = "Nama tidak ditemukan";
                const productImg = card.querySelector('img[type="product"]');
                if (productImg && productImg.alt && productImg.alt.trim()) {
                    title = productImg.alt.trim();
                } else {
                    const titleLink = card.querySelector('a[title]');
                    if (titleLink) {
                        title = titleLink.getAttribute('title');
                    }
                }

                let price_rp = 0;
                let price_original = 0;
                let discount_percent = 0;
                let rating = 0;
                let sold_count = 0;
                let shop = "Lazada Seller";
                let location = "Lokasi tidak diketahui";

                // 4. Ekstrak HARGA - Target div.aBrP0 > span.ooOxS
                const priceSpan = card.querySelector('span.ooOxS');
                if (priceSpan) {
                    const priceText = priceSpan.textContent;
                    const priceMatch = priceText.match(/Rp\\s*([\\d.]+)/);
                    if (priceMatch) {
                        price_rp = parseInt(priceMatch[1].replace(/\\./g, ''));
                        price_original = price_rp;
                    }
                }

                // 5. Ekstrak DISKON - Target badge "Voucher save XX%" atau "% Off"
                const discountBadge = card.querySelector('.ic-dynamic-badge-120014');
                if (discountBadge) {
                    const badgeText = discountBadge.textContent;
                    const match = badgeText.match(/save\\s*(\\d+)%/i);
                    if (match) {
                        discount_percent = parseInt(match[1]);
                    }
                }
                // Fallback: cari pattern "% Off"
                if (discount_percent === 0) {
                    const offBadge = card.querySelector('span.IcOsH');
                    if (offBadge) {
                        const offMatch = offBadge.textContent.match(/(\\d+)%\\s*Off/i);
                        if (offMatch) {
                            discount_percent = parseInt(offMatch[1]);
                        }
                    }
                }

                // 6. Ekstrak TERJUAL - Target span dengan text "X sold"
                const soldElements = card.querySelectorAll('span');
                for (const span of soldElements) {
                    const text = span.textContent?.trim() || '';
                    if (/sold$/.test(text)) {
                        sold_count = parseSoldCount(text);
                        break;
                    }
                }

                // 7. Ekstrak LOKASI - Target span.oa6ri dengan attribute title
                const locationEl = card.querySelector('span.oa6ri');
                if (locationEl) {
                    const locTitle = locationEl.getAttribute('title');
                    if (locTitle && locTitle.trim()) {
                        location = locTitle.trim();
                    }
                }

                // 8. Ekstrak RATING - Cari element dengan class mengandung "rating" atau "star"
                const ratingEl = card.querySelector('[class*="rating"], [class*="star"]');
                if (ratingEl) {
                    const ratingText = ratingEl.textContent.match(/([0-9.]+)/);
                    if (ratingText) {
                        rating = parseFloat(ratingText[1]);
                    }
                }

                // Validasi & Simpan
                if (price_rp > 0 && title !== "Nama tidak ditemukan") {
                    results.push({
                        search_keyword: searchKeyword || '',
                        category: [searchKeyword || ''],
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
                        marketplace: "Lazada",
                    });
                }
            });
            return results;
        }
        """,
        keyword,
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

        # 1. Wait untuk load data
        await page.wait_for_timeout(2000)

        # 2 Extract Data Mentah
        data: List[Dict[str, Any]] = await extract_data(page, keyword)

        if data:
            print(f"[*] Memproses {len(data)} produk untuk disimpan ke database...")

            # 4. Simpan ke Database
            db.insert_products(data, source_marketplace="Lazada", search_keyword=keyword)
        else:
            print("[-] Tidak ada data yang diekstrak. (Mungkin terhalang Anti-bot/Struktur berubah)")

        print("\n✓ Proses selesai. Browser ditutup dengan sukses.")
        await browser.close()