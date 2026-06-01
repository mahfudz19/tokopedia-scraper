import asyncio
import time
from typing import List, Dict, Any, Optional
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from src.database import db

def scroll_to_bottom_selenium(driver, max_attempts=80) -> None:
    """Balanced scroll: cepat tapi tetap beri waktu lazy-load Shopee."""
    print("\n[*] Memulai proses auto-scroll ke bawah halaman (Balanced Mode)...")
    
    # Dapatkan viewport height dan hitung scroll step optimal
    viewport_height = driver.execute_script("return window.innerHeight")
    scroll_step = int(viewport_height * 1.5)  # 1.5x viewport = balance speed & lazy-load
    
    attempts = 0
    last_scroll_position = driver.execute_script("return window.scrollY")
    consecutive_no_scroll = 0
    max_consecutive_no_scroll = 3

    while attempts < max_attempts:
        # Scroll dengan jarak optimal (1.5x viewport)
        driver.execute_script(f"window.scrollBy(0, {scroll_step})")
        time.sleep(1)  # 1 detik untuk lazy-load gambar (cukup untuk Susercontent CDN)
        
        new_scroll_position = driver.execute_script("return window.scrollY")
        
        if new_scroll_position == last_scroll_position:
            consecutive_no_scroll += 1
            if consecutive_no_scroll >= max_consecutive_no_scroll:
                print("[✓] Sudah mencapai bagian bawah halaman.")
                break
            # Final check - scroll ke paling bawah
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            final_scroll = driver.execute_script("return window.scrollY")
            if final_scroll == last_scroll_position:
                print("[✓] Sudah mencapai bagian bawah halaman.")
                break
        else:
            consecutive_no_scroll = 0
            
        last_scroll_position = new_scroll_position
        attempts += 1


def extract_data_selenium(driver, keyword: str) -> List[Dict[str, Any]]:
    """Mengekstrak data produk Shopee dengan optimized extraction."""
    print(f"\n[*] Mengekstrak data produk Shopee untuk keyword: '{keyword}'...")

    js_code = r"""
    return (function(searchKeyword) {
        const results = [];
        const cards = document.querySelectorAll('li[data-sqe="item"]');
        
        cards.forEach(card => {
            // 1. URL - dari link produk Shopee
            const aTag = card.querySelector('a[href*="-i."]');
            if (!aTag) return;
            
            let raw_url = aTag.getAttribute('href');
            if (raw_url && !raw_url.startsWith('http')) {
                raw_url = 'https://shopee.co.id' + raw_url;
            }
            const url = raw_url ? raw_url.split('?')[0] : "";
            
            // 2. Nama Produk - dari aria-label
            let name = "Nama tidak ditemukan";
            const ariaLabel = aTag.getAttribute('aria-label');
            if (ariaLabel && ariaLabel.startsWith('View product:')) {
                name = ariaLabel.replace('View product:', '').trim();
            }
            
            // 3. Harga - textNodes approach (terbukti bekerja)
            let price_rp = 0;
            const textNodes = Array.from(card.querySelectorAll('*'))
                .filter(el => el.children.length === 0 && el.textContent.trim().length > 0)
                .map(el => el.textContent.trim());
            
            // Cari pattern "Rp XXXXX" atau "Rp" diikuti angka
            textNodes.forEach((t, index) => {
                if (t === "Rp" && index + 1 < textNodes.length) {
                    const numStr = textNodes[index+1].replace(/[^0-9]/g, '');
                    if (numStr) price_rp = parseInt(numStr);
                }
                if (t.startsWith("Rp")) {
                    const numStr = t.replace(/[^0-9]/g, '');
                    if (numStr && numStr.length > 4) price_rp = parseInt(numStr);
                }
            });
            
            // 4. Lokasi - dari aria-label location-*
            let location = "Lokasi tidak diketahui";
            const locNode = card.querySelector('[aria-label^="location-"]');
            if (locNode) {
                location = locNode.getAttribute('aria-label').replace('location-', '').trim();
            }
            
            // Validasi dan simpan (tanpa shop karena tidak tersedia di Shopee)
            if (url && name !== "Nama tidak ditemukan" && price_rp > 0) {
                results.push({ url, name, price_rp, location });
            }
        });
        
        return results;
    })(arguments[0]);
    """
    
    result = driver.execute_script(js_code, keyword)
    print(f"    [✓] Total produk diekstrak: {len(result)}")
    return result


def run_shopee_selenium(keyword: str, show_head: bool) -> List[Dict[str, Any]]:
    mode_text = "HEADFUL (UI Terbuka)" if show_head else "HEADLESS (Background)"
    print(f"--- Membuka Browser dengan Undetected-Chromedriver [{mode_text}] ---")

    options = uc.ChromeOptions()
    
    options.add_argument("--disable-blink-features=AutomationControlled")

    if not show_head:
        options.add_argument("--headless=new")
        options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    user_data_dir = "./shopee_profile_uc"

    print("[*] Meluncurkan browser Chrome murni...")
    driver = uc.Chrome(
        options=options,
        user_data_dir=user_data_dir,
        headless=False,  
        version_main=148,
    )
    driver.maximize_window()

    print("[*] Membuka beranda Shopee untuk injeksi pengaturan...")
    driver.get("https://shopee.co.id")
    
    # Wait untuk homepage load dengan explicit wait (lebih cepat dari fixed sleep)
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
    except TimeoutException:
        time.sleep(1)  # Fallback jika wait timeout
    
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

    # Reduced polling time dari 10 detik menjadi 3 detik (lebih cepat)
    for i in range(3):
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
    scroll_to_bottom_selenium(driver, max_attempts=960)

    # 2. Mengekstrak Data Mentah
    data = extract_data_selenium(driver, keyword)

    driver.quit()
    return data

async def scrape_shopee_search(keyword: str, show_head: bool = False) -> Dict[str, Any]:
    """Scrape produk Shopee berdasarkan keyword dan simpan ke database.

    Returns:
        Dict dengan keys: success, keyword, products_count, db_new, db_updated, duration, error
    """
    start_time = time.time()

    try:
        # 1. Jalankan Selenium secara Asinkron
        data = await asyncio.to_thread(run_shopee_selenium, keyword, show_head)

        # 2. Simpan ke MongoDB dan dapatkan stats
        db_new = 0
        db_updated = 0

        if data:
            result = db.insert_products(data, source_marketplace="Shopee", search_keyword=keyword)
            if result:
                db_new = result.get("new", 0)
                db_updated = result.get("updated", 0)

            products_count = len(data)
        else:
            products_count = 0

        duration = time.time() - start_time

        return {
            "success": True,
            "keyword": keyword,
            "products_count": products_count,
            "db_new": db_new,
            "db_updated": db_updated,
            "duration": duration,
            "error": None
        }

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)

        # Handle special case untuk CAPTCHA
        if "CAPTCHA_BLOCK" in error_msg:
            error_msg = "CAPTCHA_BLOCK"

        return {
            "success": False,
            "keyword": keyword,
            "products_count": 0,
            "db_new": 0,
            "db_updated": 0,
            "duration": duration,
            "error": error_msg[:100]
        }