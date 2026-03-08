import asyncio
import random
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def scrape_find_page(keyword, max_pages=1):
    """
    Fungsi untuk melakukan scraping harga dari rute /find/{keyword}
    """
    results = []
    os.makedirs("data", exist_ok=True)

    async with async_playwright() as p:
        # Menggunakan Chromium, headless=False agar kita bisa pantau
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        # --- TERAPKAN MODE STEALTH DI SINI ---
        # Ini akan menghapus jejak 'webdriver' dan meniru browser asli

        print(f"[*] Memulai scraping untuk keyword: '{keyword}'")

        for current_page in range(1, max_pages + 1):
            url = f"https://www.tokopedia.com/find/{keyword}?utm_source=google&amp;utm_medium=organic&amp;utm_campaign=find&page=1"
            print(f"\n[+] Mengakses Halaman {current_page}: {url}")

            try:
                # Tambahkan timeout yang sedikit lebih panjang (60 detik) 
                # karena sistem anti-bot kadang membuat loading lebih lama
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Random delay agar terlihat seperti manusia
                await page.wait_for_timeout(random.randint(3000, 5000))

                # Deteksi jika terkena 404 (Produk tidak ada / diblokir sementara)
                is_404 = await page.locator("text='Waduh, tujuanmu nggak ada!'").count()
                if is_404 > 0:
                    print(f"[-] Halaman {current_page} mengembalikan 404. Melewati halaman ini...")
                    continue

                # Scroll perlahan untuk memicu lazy-load gambar dan elemen DOM
                for _ in range(3):
                    await page.mouse.wheel(0, 800)
                    await page.wait_for_timeout(1000)

                # EKSTRAKSI DATA
                product_cards = await page.locator("div[data-testid='master-product-card']").all()
                
                if not product_cards:
                    print("[!] Tidak menemukan kartu produk. Mungkin selector CSS berubah.")
                    continue

                print(f"[+] Ditemukan {len(product_cards)} produk di halaman {current_page}.")

                for card in product_cards:
                    try:
                        title_el = card.locator("div[data-testid='spnSRPProdName']")
                        title = await title_el.inner_text() if await title_el.count() > 0 else "Nama tidak ditemukan"

                        price_el = card.locator("div[data-testid='spnSRPProdPrice']")
                        price = await price_el.inner_text() if await price_el.count() > 0 else "Harga tidak ditemukan"

                        clean_price = price.replace("Rp", "").replace(".", "").strip()

                        if title != "Nama tidak ditemukan" and clean_price.isdigit():
                            results.append({
                                "keyword": keyword,
                                "name": title,
                                "price_rp": int(clean_price),
                                "scraped_at": datetime.now().isoformat()
                            })
                    except Exception as e:
                        print(f"[-] Gagal mengekstrak satu produk: {e}")
                        continue

            except Exception as e:
                print(f"[!] Terjadi error saat memuat halaman {current_page}: {e}")
                break 

        await browser.close()

    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/tokopedia_{keyword}_{timestamp}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"\n[v] Scraping selesai! {len(results)} data berhasil disimpan di {filename}")
    else:
        print("\n[!] Scraping selesai, tapi tidak ada data yang berhasil diekstrak.")

if __name__ == "__main__":
    test_keyword = "tempat-bekal-piknik-set"
    asyncio.run(scrape_find_page(test_keyword, max_pages=1))