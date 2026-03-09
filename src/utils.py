import json
import os
from typing import List, Dict, Any
from playwright.async_api import Page, Locator


async def save_page_as_mhtml(page: Page, keyword: str, page_number: str) -> None:
    """Menyimpan halaman web mentah ke format MHTML untuk backup visual."""
    print(f"[*] Menyimpan halaman {page_number} sebagai MHTML...")
    folder_path = f"data/tokopedia_{keyword}_page_{page_number}"
    os.makedirs(folder_path, exist_ok=True)
    
    client = await page.context.new_cdp_session(page)
    snapshot = await client.send("Page.captureSnapshot", {"format": "mhtml"})
    
    file_path = f"{folder_path}/index.mhtml"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(snapshot["data"])
        
    print(f"[v] Berhasil menyimpan MHTML: {file_path}")


async def save_data_to_json(data: List[Dict[str, Any]], keyword: str, page_number: str) -> None:
    """Menyimpan hasil ekstraksi data (List of Dictionaries) ke format JSON."""
    if not data:
        return
        
    folder_path = f"data/tokopedia_{keyword}_page_{page_number}"
    os.makedirs(folder_path, exist_ok=True)
    
    file_path = f"{folder_path}/data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"[v] Berhasil menyimpan {len(data)} produk ke JSON: {file_path}")


async def scroll_to_element(page: Page, element_selector: str, max_attempts: int = 30) -> Locator:
    """Melakukan scroll dinamis hingga elemen yang dituju terlihat di layar."""
    print(f"\n[*] Memulai auto-scroll mencari: {element_selector}")
    target_locator: Locator = page.locator(element_selector)
    attempts: int = 0
    
    last_scroll_height: int = await page.evaluate("document.body.scrollHeight")
    
    while attempts < max_attempts:
        if await target_locator.is_visible():
            print("✓ Elemen target ditemukan di layar!")
            break 
        
        tinggi_layar: int = await page.evaluate("window.innerHeight")
        await page.mouse.wheel(0, tinggi_layar - 100)
        await page.wait_for_timeout(1500) 
        
        new_scroll_height: int = await page.evaluate("document.body.scrollHeight")
        if new_scroll_height == last_scroll_height:
            print("[i] Mentok di bawah halaman. Asumsi: Produk habis (Hanya 1 halaman).")
            break
            
        last_scroll_height = new_scroll_height
        attempts += 1
        
    if attempts == max_attempts:
        print("[!] Peringatan: Berhenti setelah batas maksimal scroll mencapai batas.")
        
    return target_locator