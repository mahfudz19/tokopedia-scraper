import json
import os
from datetime import datetime


async def save_page_as_mhtml(page, keyword, page_number):
    """
    Menyimpan halaman yang sudah di-render ke format MHTML.
    """
    print(f"[*] Menyimpan halaman {page_number} sebagai MHTML...")
    os.makedirs(f"data/tokopedia_{keyword}_page_{page_number}", exist_ok=True)

    client = await page.context.new_cdp_session(page)
    snapshot = await client.send("Page.captureSnapshot", {"format": "mhtml"})

    file_path = f"data/tokopedia_{keyword}_page_{page_number}/index.mhtml"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(snapshot["data"])

    print(f"[v] Berhasil menyimpan MHTML: {file_path}")


async def scroll_to_element(page, element_selector, max_attempts=30):
    """
    Melakukan scroll ke bawah secara bertahap sampai selector yang dituju terlihat.
    Dilengkapi deteksi 'mentok bawah' untuk halaman yang hanya memiliki 1 page.
    """
    print(f"\n[*] Memulai auto-scroll mencari: {element_selector}")
    target_locator = page.locator(element_selector)
    attempts = 0

    # Mencatat tinggi halaman awal
    last_scroll_height = await page.evaluate("document.body.scrollHeight")

    while attempts < max_attempts:
        if await target_locator.is_visible():
            print("✓ Elemen target ditemukan di layar!")
            break

        tinggi_layar = await page.evaluate("window.innerHeight")
        jarak_scroll = tinggi_layar - 100
        await page.mouse.wheel(0, jarak_scroll)

        # Jeda 1.5 detik untuk memastikan skeleton loading selesai
        await page.wait_for_timeout(3000)

        # Mengecek apakah tinggi halaman bertambah setelah di-scroll
        new_scroll_height = await page.evaluate("document.body.scrollHeight")

        if new_scroll_height == last_scroll_height:
            print(
                "[i] Mentok di bawah halaman. Asumsi: Produk habis (Hanya 1 halaman)."
            )
            break

        last_scroll_height = new_scroll_height
        attempts += 1

    if attempts == max_attempts:
        print("[!] Peringatan: Berhenti setelah batas maksimal scroll mencapai batas.")

    return target_locator
