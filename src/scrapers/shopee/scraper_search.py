import asyncio
import time
import os
import json
from typing import List, Dict, Any
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Import koneksi database MongoDB
from src.database import db


def scroll_to_bottom_selenium(driver, max_attempts=15) -> None:
    """Melakukan scroll secara perlahan agar lazy-load Shopee terpicu"""
    print("\n[*] Memulai proses auto-scroll ke bawah halaman...")
    attempts = 0
    last_scroll_position = driver.execute_script("return window.scrollY")

    while attempts < max_attempts:
        # Scroll perlahan (setengah tinggi layar) agar gambar produk sempat dimuat
        driver.execute_script("window.scrollBy(0, window.innerHeight / 1.5)")
        time.sleep(1.5)
        new_scroll_position = driver.execute_script("return window.scrollY")

        if new_scroll_position == last_scroll_position:
            # Jika mentok, coba scroll paksa ke dasar halaman
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            final_scroll = driver.execute_script("return window.scrollY")
            if final_scroll == last_scroll_position:
                print("[✓] Sudah mencapai bagian bawah halaman.")
                break

        last_scroll_position = new_scroll_position
        attempts += 1


def extract_data_selenium(driver) -> List[Dict[str, Any]]:
    """Mengekstrak data produk menggunakan DOM Selectors berdasarkan struktur terbaru Shopee"""
    print("\n[*] Mengekstrak data produk Shopee...")

    js_script = """
    const results = [];
    // Mengambil semua elemen list yang memiliki atribut data-sqe="item"
    const items = document.querySelectorAll('li[data-sqe="item"]'); 
    
    items.forEach(li => {
        // 1. Ambil URL Produk
        const aTag = li.querySelector('a[href*="-i."]');
        if (!aTag) return; // Jika ini bukan kotak produk (misal skeleton loading), lewati
        
        const url = aTag.href.split('?')[0]; // Bersihkan URL
        
        // 2. Ambil Judul Produk
        let title = "Nama tidak ditemukan";
        const titleEl = li.querySelector('div.line-clamp-2, div.break-words');
        if (titleEl) {
            // textContent lebih aman dari innerText karena mengabaikan tag <img> (seperti flag-label)
            title = titleEl.textContent.trim();
        }

        // 3. Ambil Harga Produk
        let price = 0;
        // Shopee menyimpan harga di dalam div dengan class items-baseline
        const priceDiv = li.querySelector('div.flex.items-baseline');
        if (priceDiv) {
            // Mengambil semua teks (cth: "Rp14.850.000") dan hanya menyisakan angka
            const priceStr = priceDiv.textContent.replace(/[^0-9]/g, '');
            if (priceStr) {
                price = parseInt(priceStr);
            }
        }

        // 4. Ambil Lokasi Toko
        let location = "Lokasi tidak diketahui";
        // Mencari ikon lokasi, lalu mengambil teks dari elemen pembungkusnya
        const locationIcon = li.querySelector('img[alt="location-icon"]');
        if (locationIcon && locationIcon.parentElement) {
            location = locationIcon.parentElement.textContent.trim();
        }

        // Hanya masukkan ke keranjang jika data utamanya valid (bukan iklan kosong)
        if (price > 0 && title !== "Nama tidak ditemukan" && title !== "") {
            results.push({ 
                name: title, 
                price_rp: price, 
                shop: "Shopee Seller", 
                location: location, 
                url: url 
            });
        }
    });
    
    // Hapus data duplikat berdasarkan URL
    const uniqueResults = Array.from(new Map(results.map(item => [item.url, item])).values());
    return uniqueResults;
    """
    extracted_data = driver.execute_script(js_script)
    return extracted_data


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
        json.dump(data, f, ensure_ascii=False, indent=4)
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


def run_shopee_selenium(keyword: str) -> None:
    print("--- Step 1: Membuka Browser dengan Undetected-Chromedriver ---")

    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")

    user_data_dir = "./shopee_profile_uc"

    print("[*] Meluncurkan browser Chrome murni (Binary Patched)...")
    driver = uc.Chrome(options=options, user_data_dir=user_data_dir, version_main=146)

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

    # --- LOGIKA DETEKSI REDIRECT SPA ---
    print("\n[*] Menunggu dan memantau perubahan URL (SPA Redirect)...")
    blacklist = [
        "/login",
        "/captcha",
        "/verify",
        "/security",
        "/check",
        "/auth",
        "/error",
    ]
    is_redirected = False

    for i in range(10):
        current_url = driver.current_url.lower()
        if any(word in current_url for word in blacklist):
            is_redirected = True
            print(f"    [!] Detik ke-{i+1}: URL berubah menjadi: {current_url}")
            break
        time.sleep(1)

    # --- BLOK INTERVENSI MANUAL ---
    if is_redirected:
        print("\n[-] TERDETEKSI REDIRECT KE CAPTCHA / LOGIN!")
        while True:
            input(
                "\n[!] TINDAKAN DIBUTUHKAN:"
                "\n    1. Selesaikan puzzle CAPTCHA atau Login secara manual di browser."
                "\n    2. Setelah berhasil lolos, tekan ENTER di sini untuk melanjutkan..."
            )
            print("\n[*] Mengecek kembali status URL...")
            current_url_clean = driver.current_url.lower().split("?")[0]
            if any(word in current_url_clean for word in blacklist):
                print(
                    f"[-] GAGAL: Anda masih terdeteksi di halaman pemblokiran (URL: {driver.current_url})."
                )
            else:
                print("[✓] BERHASIL! Anda telah terverifikasi.")
                break
    else:
        print(
            "\n[✓] AMAN! Halaman berhasil dimuat tanpa redirect ke halaman pemblokiran."
        )

    # ==========================================
    # --- PROSES SCRAPING & PENYIMPANAN DATA ---
    # ==========================================
    active_page_number = "1"

    # PERUBAHAN KRUSIAL: Tunggu Produk Muncul Sebelum Scroll!
    print("\n[*] Menunggu elemen produk selesai dirender oleh Shopee...")
    try:
        # Satpam menatap layar maksimal 20 detik sampai minimal ada 1 link produk ('a[href*="-i."]')
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'li a[href*="-i."]'))
        )
        print("[✓] Elemen produk terdeteksi di layar. Mulai memanen data!")
    except TimeoutException:
        print(
            "[-] Waktu habis (20 detik). Halaman mungkin kosong, internet lambat, atau struktur berubah."
        )
        # Lanjut saja, siapa tahu masih bisa diekstrak

    # 1. Melakukan Scroll
    scroll_to_bottom_selenium(driver, max_attempts=15)

    # 2. Mengekstrak Data
    data = extract_data_selenium(driver)

    # 3. Mendistribusikan Data
    if data:
        save_data_to_json_sync(data, keyword, active_page_number, prefix="shopee")
        db.insert_products(data, source_marketplace="Shopee")
    else:
        print(
            "\n[-] Tidak ada data yang diekstrak. Mungkin struktur HTML Shopee sedang berubah."
        )

    # 4. Melakukan Backup Visual (MHTML)
    save_page_as_mhtml_sync(driver, keyword, active_page_number, prefix="shopee")

    print("\n✓ Proses Shopee selesai. Browser ditutup dengan sukses.")
    driver.quit()


async def scrape_shopee_search(keyword: str) -> None:
    await asyncio.to_thread(run_shopee_selenium, keyword)
