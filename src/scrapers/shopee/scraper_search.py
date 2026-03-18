import asyncio
import os
from playwright.async_api import async_playwright
from dotenv import load_dotenv

# Kita buang playwright_stealth sepenuhnya!

load_dotenv()


async def scrape_shopee_search(keyword: str) -> None:
    print("--- Step 1: Membuka Browser & Proses Login Shopee ---")

    async with async_playwright() as p:
        # Hanya gunakan argumen bawaan ini untuk menyembunyikan flag "WebDriver"
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Kita biarkan Playwright menggunakan User-Agent aslinya sendiri
        context = await browser.new_context()

        print("[*] Mengatur bahasa default ke Indonesia (id)...")
        await context.add_cookies(
            [
                {
                    "name": "language",
                    "value": "id",
                    "domain": ".shopee.co.id",
                    "path": "/",
                }
            ]
        )

        page = await context.new_page()

        print("[*] Membuka halaman login Shopee...")
        await page.goto(
            "https://shopee.co.id/buyer/login", wait_until="domcontentloaded"
        )

        shopee_user = os.getenv("SHOPEE_USER")
        shopee_pass = os.getenv("SHOPEE_PASS")

        if not shopee_user or not shopee_pass:
            print("[!] Error: Kredensial Shopee tidak ditemukan di .env!")
            return

        print("[*] Menunggu kolom input...")
        await page.wait_for_selector('input[name="loginKey"]')
        await asyncio.sleep(2)

        print("[*] Mengetikkan username...")
        await page.locator('input[name="loginKey"]').click()
        await page.locator('input[name="loginKey"]').press_sequentially(
            shopee_user, delay=150
        )

        await asyncio.sleep(1)

        print("[*] Mengetikkan password...")
        await page.locator('input[name="password"]').click()
        await page.locator('input[name="password"]').press_sequentially(
            shopee_pass, delay=100
        )

        await asyncio.sleep(1)

        print("[*] Klik tombol Log In...")
        await page.click('button:has-text("Log In")')

        print("\n" + "=" * 50)
        print("[!] PERHATIAN: JIKA MUNCUL PUZZLE CAPTCHA,")
        print("    SILAKAN GESER SECARA MANUAL DI BROWSER.")
        print("    (Bot sedang menunggu selama 2 menit...)")
        print("=" * 50 + "\n")

        try:
            is_logged_in = False

            # Melakukan polling setiap 1 detik selama maksimal 120 detik (2 menit)
            for _ in range(120):
                # 1. Cek apakah kita dilempar ke rute /verify/captcha
                if "verify/captcha" in page.url:
                    # Lempar Exception agar langsung masuk ke blok except di bawah
                    raise Exception(
                        "Terdeteksi sistem Anti-Bot Datadome (Redirect ke /verify/captcha)."
                    )

                # 2. Cek apakah login sukses (kotak pencarian beranda sudah muncul)
                if await page.locator(
                    "input.shopee-searchbar-input__input"
                ).is_visible():
                    print("[✓] Pintu berhasil ditembus! Anda berstatus Login.")
                    is_logged_in = True
                    break  # Keluar dari loop karena sukses

                # Jeda 1 detik sebelum mengecek ulang
                await asyncio.sleep(1)

            # Jika loop selesai tapi masih belum login
            if not is_logged_in:
                raise Exception("Waktu habis (Timeout 120 detik) menunggu login.")

        except Exception as e:
            print(f"\n[-] PROSES DIHENTIKAN: {e}")
            print("[i] Menutup browser untuk menghindari deteksi lebih lanjut.")
            await browser.close()
            return

        # --- LOGIKA PENCARIAN NATURAL ---
        print(f"\n[*] Mengetikkan kata kunci pencarian: '{keyword}' di beranda...")

        # 1. Klik kotak pencarian di beranda
        search_input = page.locator("input.shopee-searchbar-input__input")
        await search_input.click()

        # 2. Ketik keyword perlahan layaknya manusia
        await search_input.press_sequentially(keyword, delay=150)
        await asyncio.sleep(1)  # Jeda sebelum menekan Enter

        # 3. Tekan tombol Enter di keyboard
        print("[*] Menekan tombol Enter untuk mencari...")
        await page.keyboard.press("Enter")

        print("[i] Menunggu hasil pencarian dimuat...")
        # Tunggu sampai halaman selesai memuat ulang
        await page.wait_for_load_state("domcontentloaded")

        # Cek apakah tiba-tiba dilempar ke captcha setelah menekan Enter
        if "verify/captcha" in page.url:
            print("\n[-] TERDETEKSI DATADOME SAAT MENCARI!")
        else:
            print("[✓] Selesai! Halaman terbuka dengan status akun login tanpa blokir.")

        print(
            "[i] Browser akan dibiarkan terbuka selama 5 menit agar bisa Anda pantau."
        )

        await asyncio.sleep(300)
        await browser.close()
