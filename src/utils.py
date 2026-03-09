import json
import os
from typing import List, Dict, Any
from playwright.async_api import Page, Locator


async def save_page_as_mhtml(
    page: Page, keyword: str, page_number: str, prefix: str = "tokopedia"
) -> None:
    """Menyimpan halaman web mentah ke format MHTML untuk backup visual."""
    print(f"[*] Menyimpan halaman {page_number} sebagai MHTML...")
    folder_path = f"data/{prefix}_{keyword}_page_{page_number}"
    os.makedirs(folder_path, exist_ok=True)

    client = await page.context.new_cdp_session(page)
    snapshot = await client.send("Page.captureSnapshot", {"format": "mhtml"})

    file_path = f"{folder_path}/index.mhtml"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(snapshot["data"])

    print(f"[v] Berhasil menyimpan MHTML: {file_path}")


async def save_data_to_json(
    data: List[Dict[str, Any]],
    keyword: str,
    page_number: str,
    prefix: str = "tokopedia",
) -> None:
    """Menyimpan hasil ekstraksi data (List of Dictionaries) ke format JSON."""
    if not data:
        return

    folder_path = f"data/{prefix}_{keyword}_page_{page_number}"
    os.makedirs(folder_path, exist_ok=True)

    file_path = f"{folder_path}/data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"[v] Berhasil menyimpan {len(data)} produk ke JSON: {file_path}")


async def scroll_to_bottom(page: Page, max_attempts: int = 30) -> None:
    """Melakukan scroll ke bawah secara bertahap untuk memicu lazy-load gambar/data sampai mentok."""
    print("\n[*] Memulai proses auto-scroll ke bawah halaman...")
    attempts: int = 0

    last_scroll_position: float = await page.evaluate("window.scrollY")

    while attempts < max_attempts:
        # Scroll sejauh 1 layar penuh
        await page.evaluate("window.scrollBy(0, window.innerHeight)")
        # Beri jeda agar data/gambar termuat
        await page.wait_for_timeout(1500)

        new_scroll_position: float = await page.evaluate("window.scrollY")

        # Jika posisi tidak turun lagi, berarti sudah mentok bawah
        if new_scroll_position == last_scroll_position:
            print("[✓] Sudah mencapai bagian bawah halaman.")
            break

        last_scroll_position = new_scroll_position
        attempts += 1

    if attempts == max_attempts:
        print("[!] Berhenti scroll: Mencapai batas maksimal percobaan.")
