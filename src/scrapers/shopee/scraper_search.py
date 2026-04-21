import asyncio
import time
import os
import json
from datetime import datetime
from typing import List, Dict, Any
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.utils import save_page_as_mhtml, upload_image_to_s3
from src.database import db

def scroll_to_bottom_selenium(driver, max_attempts=15) -> None:
    """Melakukan scroll secara perlahan agar lazy-load Shopee terpicu"""
    print("\n[*] Memulai proses auto-scroll ke bawah halaman (Mode Lambat untuk Shopee)...")
    attempts = 0
    last_scroll_position = driver.execute_script("return window.scrollY")

    while attempts < max_attempts:
        driver.execute_script("window.scrollBy(0, window.innerHeight)")
        time.sleep(2) # Jeda krusial agar gambar Susercontent dimuat
        new_scroll_position = driver.execute_script("return window.scrollY")

        if new_scroll_position == last_scroll_position:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            final_scroll = driver.execute_script("return window.scrollY")
            if final_scroll == last_scroll_position:
                print("[✓] Sudah mencapai bagian bawah halaman.")
                break

        last_scroll_position = new_scroll_position
        attempts += 1


def extract_data_selenium(driver, keyword: str) -> List[Dict[str, Any]]:
    """Mengekstrak data komprehensif dari DOM Shopee menggunakan Heuristik"""
    print(f"\n[*] Mengekstrak data produk Shopee untuk keyword: '{keyword}'...")

    # Menggunakan raw string (r"") untuk menghindari SyntaxWarning invalid escape sequence
    js_code = r"""
    return (function(searchKeyword) {
        const results = [];
        // Shopee biasanya menggunakan atribut data-sqe="item" untuk kartu produk
        const cards = document.querySelectorAll('li[data-sqe="item"], div[data-sqe="item"]');
        
        cards.forEach(card => {
            const aTag = card.querySelector('a[data-sqe="link"]') || card.querySelector('a[href*="-i."]');
            if (!aTag) return; 
            
            // 1. Identifikasi URL & ID
            let raw_url = aTag.getAttribute('href');
            if (raw_url && !raw_url.startsWith('http')) {
                raw_url = 'https://shopee.co.id' + raw_url;
            }
            const clean_url = raw_url ? raw_url.split('?')[0] : "";
            
            // ID Shopee selalu ada di akhir URL: -i.[SHOP_ID].[PRODUCT_ID]
            let marketplace_product_id = clean_url;
            if (clean_url.includes('-i.')) {
                const parts = clean_url.split('.');
                if (parts.length > 0) {
                    marketplace_product_id = parts[parts.length - 1];
                }
            }

            // 2. Ekstrak NAMA PRODUK
            let title = "Nama tidak ditemukan";
            // Mencari di aria-label link utama
            const ariaLabel = aTag.getAttribute('aria-label');
            if (ariaLabel && ariaLabel.startsWith('View product:')) {
                title = ariaLabel.replace('View product:', '').trim();
            } else {
                // Fallback ke aria-label di wrapper div
                const cardDiv = card.querySelector('div[aria-label^="Product card:"]');
                if (cardDiv) {
                    title = cardDiv.getAttribute('aria-label').replace('Product card:', '').trim();
                } else {
                    const img = card.querySelector('img[alt]');
                    if (img && img.alt && img.alt !== "custom-overlay") title = img.alt;
                }
            }

            // 3. Ekstrak Image URL Mentah
            let image_url_raw = null;
            const imgTag = card.querySelector('picture img') || card.querySelector('img.lazyload') || card.querySelector('img');
            if (imgTag) {
                // Hindari gambar webp resolusi kecil jika memungkinkan, ambil src utama
                image_url_raw = imgTag.src;
            }

            // Kumpulkan Text Nodes untuk harga, terjual, dan rating
            const textNodes = Array.from(card.querySelectorAll('*'))
                .filter(el => el.children.length === 0 && el.textContent.trim().length > 0)
                .map(el => el.textContent.trim());

            // 4. Ekstrak HARGA (Mencari teks "Rp" atau teks berawalan Rp)
            let prices = [];
            textNodes.forEach((t, index) => {
                if (t === "Rp" && index + 1 < textNodes.length) {
                    const numStr = textNodes[index+1].replace(/[^0-9]/g, '');
                    if (numStr) prices.push(parseInt(numStr));
                }
            });
            textNodes.filter(t => t.startsWith("Rp")).forEach(rp => {
                const numStr = rp.replace(/[^0-9]/g, '');
                if (numStr) prices.push(parseInt(numStr));
            });

            let price_rp = 0;
            let price_original = 0;
            if (prices.length > 0) {
                price_original = Math.max(...prices);
                price_rp = Math.min(...prices);
            }

            // 5. Ekstrak DISKON
            let discount_percent = 0;
            const discountMatch = textNodes.find(t => t.includes('%'));
            if (discountMatch) {
                const num = discountMatch.match(/(\d+)/);
                if(num) discount_percent = parseInt(num[0]) || 0;
            }

            // 6. Ekstrak RATING
            let rating = 0;
            const ratingStr = textNodes.find(t => t.match(/^[0-5]\.[0-9]$/));
            if(ratingStr) rating = parseFloat(ratingStr) || 0;

            // 7. Ekstrak TERJUAL
            let sold_count = 0;
            const soldStr = textNodes.find(t => t.toLowerCase().includes("terjual"));
            if (soldStr) {
                let s = soldStr.toLowerCase().replace("terjual", "").replace(/\+/g, "").trim();
                if (s.includes("rb")) {
                    sold_count = parseInt(parseFloat(s.replace("rb", "").replace(",", ".")) * 1000);
                } else if (s.includes("k")) {
                    sold_count = parseInt(parseFloat(s.replace("k", "").replace(",", ".")) * 1000);
                } else {
                    sold_count = parseInt(s) || 0;
                }
            }

            // 8. Ekstrak LOKASI & TOKO
            let location = "Lokasi tidak diketahui";
            // Shopee menggunakan aria-label="location-Jakarta Barat"
            const locNode = card.querySelector('[aria-label^="location-"]');
            if (locNode) {
                location = locNode.getAttribute('aria-label').replace('location-', '').trim();
            } else {
                const locText = textNodes.find(t => t.startsWith("Kota ") || t.startsWith("Kab. ") || t.startsWith("DKI "));
                if (locText) location = locText;
            }
            
            let shop = "Shopee Seller"; 

            // Validasi & Simpan
            if (price_rp > 0 && title !== "Nama tidak ditemukan") {
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
                    marketplace: "Shopee",
                });
            }
        });
        return results;
    })(arguments[0]);
    """
    
    return driver.execute_script(js_code, keyword)


def save_data_to_json_sync(
    data: List[Dict[str, Any]],
    keyword: str,
    page_number: str = "1",
    prefix: str = "shopee",
) -> None:
    if not data:
        return
    folder_path = f"data/{prefix}_{keyword}_page_{page_number}"
    os.makedirs(folder_path, exist_ok=True)
    file_path = f"{folder_path}/data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4, default=str)
    print(f"[✓] Berhasil menyimpan {len(data)} produk ke JSON: {file_path}")


def save_page_as_mhtml_sync(
    driver, keyword: str, page_number: str = "1", prefix: str = "shopee"
) -> None:
    print(f"[*] Menyimpan halaman {page_number} sebagai MHTML...")
    folder_path = f"data/{prefix}_{keyword}_page_{page_number}"
    os.makedirs(folder_path, exist_ok=True)
    file_path = f"{folder_path}/index.mhtml"

    try:
        snapshot = driver.execute_cdp_cmd("Page.captureSnapshot", {"format": "mhtml"})
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(snapshot["data"])
        print(f"[✓] Berhasil menyimpan MHTML: {file_path}")
    except Exception as e:
        print(f"[!] Gagal menyimpan MHTML: {e}")


def run_shopee_selenium(keyword: str, show_head: bool) -> List[Dict[str, Any]]:
    mode_text = "HEADFUL (UI Terbuka)" if show_head else "HEADLESS (Background)"
    print(f"--- Membuka Browser dengan Undetected-Chromedriver [{mode_text}] ---")

    options = uc.ChromeOptions()
    options.add_argument("--window-position=0,0")
    options.add_argument("--window-size=1280,720")
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")

    if not show_head:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    user_data_dir = "./shopee_profile_uc"

    print("[*] Meluncurkan browser Chrome murni...")
    driver = uc.Chrome(
        options=options,
        user_data_dir=user_data_dir,
        headless=False,  
        version_main=146,
    )

    print("[*] Membuka beranda Shopee untuk injeksi pengaturan...")
    driver.get("https://shopee.co.id")
    time.sleep(3)
    driver.add_cookie(
        {"name": "language", "value": "id", "domain": ".shopee.co.id", "path": "/"}
    )

    formatted_keyword = keyword.replace(" ", "%20")
    url = f"https://shopee.co.id/search?keyword={formatted_keyword}"

    print(f"\n[*] Membuka link pencarian Shopee: {url}")
    driver.get(url)

    print("\n[*] Menunggu dan memantau perubahan URL (SPA Redirect)...")
    blacklist = ["/login", "/captcha", "/verify", "/security", "/check", "/auth", "/error"]
    is_redirected = False

    for i in range(10):
        current_url = driver.current_url.lower()
        if any(word in current_url for word in blacklist):
            is_redirected = True
            print(f"    [!] Detik ke-{i+1}: URL berubah menjadi: {current_url}")
            break
        time.sleep(1)

    if is_redirected:
        print("\n[-] TERDETEKSI REDIRECT KE CAPTCHA / LOGIN!")

        if not show_head:
            print("    [!] Bot sedang berjalan di mode HEADLESS.")
            print("    [!] Tidak bisa menyelesaikan CAPTCHA secara otomatis.")
            print("    [!] TINDAKAN: Skrip dihentikan untuk keamanan profil.")
            print("\n=======================================================")
            print("💡 SOLUSI: Jalankan ulang perintah dengan tambahan flag --head")
            print(f'   Contoh: python main.py -k "{keyword}" -m shopee --head')
            print("=======================================================\n")
            driver.quit()
            raise RuntimeError("CAPTCHA_BLOCK")
        else:
            while True:
                input(
                    "\n[!] TINDAKAN DIBUTUHKAN:\n"
                    "    1. Selesaikan puzzle CAPTCHA atau Login secara manual di browser.\n"
                    "    2. Setelah berhasil lolos, tekan ENTER di sini untuk melanjutkan..."
                )
                print("\n[*] Mengecek kembali status URL...")
                current_url_clean = driver.current_url.lower().split("?")[0]
                if any(word in current_url_clean for word in blacklist):
                    print(f"[-] GAGAL: Anda masih terdeteksi di halaman pemblokiran (URL: {driver.current_url}).")
                else:
                    print("[✓] BERHASIL! Anda telah terverifikasi.")
                    break
    else:
        print("\n[✓] AMAN! Halaman berhasil dimuat tanpa redirect ke halaman pemblokiran.")

    active_page_number = "1"

    print("\n[*] Menunggu elemen produk selesai dirender oleh Shopee...")
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'li[data-sqe="item"] a, a[href*="-i."]'))
        )
        print("[✓] Elemen produk terdeteksi di layar. Mulai memanen data!")
    except TimeoutException:
        print("[-] Waktu habis (20 detik). Halaman mungkin kosong, internet lambat, atau struktur berubah.")

    # 1. Melakukan Scroll
    scroll_to_bottom_selenium(driver, max_attempts=15)

    # 2. Mengekstrak Data Mentah
    data = extract_data_selenium(driver, keyword)

    # 3. Melakukan Backup Visual (MHTML) & Backup Awal Json
    if data:
         save_data_to_json_sync(data, keyword, active_page_number, prefix="shopee")
    save_page_as_mhtml_sync(driver, keyword, active_page_number, prefix="shopee")

    driver.quit()
    return data

async def scrape_shopee_search(keyword: str, show_head: bool = False) -> None:
    # 1. Jalankan Selenium secara Asinkron
    data = await asyncio.to_thread(run_shopee_selenium, keyword, show_head)

    # 2. Proses S3 Upload dan Update Data setelah browser ditutup
    if data:
        print(f"\n[*] Memproses {len(data)} produk untuk S3 Upload & Formatting. Harap tunggu...")
        upload_success = 0
        upload_failed = 0

        for item in data:
            img_raw = item.get("image_url_raw")
            if img_raw:
                if img_raw.startswith("//"):
                    img_raw = "https:" + img_raw
                    
                # Upload asinkron 
                s3_url = await asyncio.to_thread(upload_image_to_s3, img_raw)
                
                if s3_url:
                    # Simpan hanya path S3-nya
                    bucket_domain = "amazonaws.com/"
                    if bucket_domain in s3_url:
                        item["image_url"] = s3_url.split(bucket_domain)[1]
                    else:
                        item["image_url"] = s3_url
                        
                    upload_success += 1
                else:
                    item["image_url"] = img_raw 
                    upload_failed += 1
            else:
                item["image_url"] = None
            
            # Buang data mentah dan set Timestamp Upsert (Tanpa createdAt)
            item.pop("image_url_raw", None)
            item["updatedAt"] = datetime.now()

        print(f"[*] Selesai! Status Upload S3: {upload_success} Gambar Berhasil, {upload_failed} Gambar Gagal.")

        # 3. Simpan ke MongoDB secara sinkron
        db.insert_products(data, source_marketplace="Shopee")
    else:
        print("\n[-] Tidak ada data yang diekstrak. Mungkin struktur HTML Shopee sedang berubah atau terhalang Captcha.")

    print("\n✓ Proses Keseluruhan Selesai.")