from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page
from playwright_stealth import stealth

from src.utils import save_page_as_mhtml, scroll_to_element, save_data_to_json
from src.database import db


async def extract_data(page: Page) -> List[Dict[str, Any]]:
    """Mengekstrak data dari DOM Lazada berdasarkan data-qa-locator."""
    print("\n[*] Mengekstrak data produk Lazada...")

    extracted_data: List[Dict[str, Any]] = await page.evaluate(
        """() => {
        const results = [];
        // Selector khusus yang selalu dipakai Lazada
        const cards = document.querySelectorAll('div[data-qa-locator="product-item"]');
        
        cards.forEach(card => {
            // TRIK JITU: Cari link <a> yang secara spesifik punya atribut 'title'
            // Ini akan langsung menunjuk ke elemen judul produk, mengabaikan link gambar!
            const titleElement = card.querySelector('a[title]');
            if (!titleElement) return; 
            
            // CLEANING URL: Buang parameter pelacakan setelah '?'
            let url = titleElement.href.split('?')[0];
            if (url.startsWith('//')) {
                url = 'https:' + url;
            }
            
            // Ambil nama produk dari atribut title
            let title = titleElement.getAttribute('title');
            
            let price = 0;
            let location = "Lokasi tidak diketahui";
            
            // Ambil seluruh teks dari card untuk mengekstrak Harga dan Lokasi
            const texts = card.innerText.split('\\n').map(t => t.trim()).filter(t => t.length > 0);
            
            for (let i = 0; i < texts.length; i++) {
                const text = texts[i];
                // Ekstraksi harga dengan deteksi "Rp"
                if (text.startsWith("Rp") && price === 0) {
                    price = parseInt(text.replace(/[^0-9]/g, '')) || 0;
                }
            }
            
            // Lokasi di Lazada hampir selalu berada di baris paling bawah
            if (texts.length > 0) {
                location = texts[texts.length - 1]; 
            }
            
            // Hanya simpan jika harga valid (hindari data sampah)
            if (price > 0 && title) {
                // Nama toko sering tersembunyi di halaman Tag, kita set default
                results.push({ 
                    name: title, 
                    price_rp: price, 
                    shop: "Lazada Seller", 
                    location: location, 
                    url: url 
                });
            }
        });
        return results;
    }"""
    )
    return extracted_data


async def scrape_lazada_tag(keyword: str) -> None:
    print("--- Step 1: Membuka Browser (Lazada) ---")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        # Wajib stealth di Lazada
        await stealth(page)

        # URL Lazada menggunakan strip "-" bukan "%20" di rute tag
        formatted_keyword = keyword.replace(" ", "-")
        url = f"https://www.lazada.co.id/tag/{formatted_keyword}/"

        print(f"[*] Mencoba membuka: {url}")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            print(f"[!] Halaman gagal dimuat (Timeout/Diblokir): {e}")
            await browser.close()
            return

        # 1. Scroll sampai ke elemen paginasi Lazada (biasanya ul.ant-pagination)
        await scroll_to_element(page, "ul.ant-pagination", max_attempts=15)

        # Sementara kita hardcode halaman 1 (bisa kita kembangkan logikanya nanti)
        active_page_number = "1"

        # 2. Extract Data Mentah
        data: List[Dict[str, Any]] = await extract_data(page)

        # 3. Distribusikan Data ke file lokal dan MongoDB
        if data:
            await save_data_to_json(data, f"lazada_{keyword}", active_page_number)
            db.insert_products(data, source_marketplace="Lazada")
        else:
            print(
                "[-] Tidak ada data yang diekstrak. Mungkin captcha muncul atau struktur CSS berubah."
            )

        # 4. Backup HTML
        await save_page_as_mhtml(page, f"lazada_{keyword}", active_page_number)

        print("\n✓ Proses Lazada selesai. Browser ditutup dengan sukses.")
        await browser.close()
