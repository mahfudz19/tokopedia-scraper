import asyncio
import os
from src.scraper_find import scrape_find_page
from src.scraper_search import scrape_search_page

async def process_from_file(filename, pilihan_metode):
    """
    Fungsi untuk membaca file txt dan melakukan looping scraping
    """
    if not os.path.exists(filename):
        print(f"\n[!] Error: File '{filename}' tidak ditemukan di folder proyek.")
        return

    # Membaca isi file dan membersihkan spasi/enter kosong
    with open(filename, 'r', encoding='utf-8') as f:
        keywords = [line.strip() for line in f.readlines() if line.strip()]

    if not keywords:
        print(f"\n[!] File '{filename}' kosong.")
        return

    print(f"\n[*] Ditemukan {len(keywords)} target di dalam '{filename}'. Memulai proses batch...")

    # Melakukan looping untuk setiap keyword di dalam file
    for index, keyword in enumerate(keywords, start=1):
        print(f"\n{'-'*30}")
        print(f"Memproses [{index}/{len(keywords)}]: {keyword}")
        print(f"{'-'*30}")

        if pilihan_metode == "1":
            await scrape_find_page(keyword, max_pages=1)
        elif pilihan_metode == "2":
            await scrape_search_page(keyword)
        
        # Berikan jeda antar keyword agar server Tokopedia tidak curiga
        if index < len(keywords):
            print(f"[*] Jeda 5 detik sebelum keyword berikutnya...")
            await asyncio.sleep(5)

async def main():
    print("="*40)
    print("🤖 TOKOPEDIA BATCH SCRAPER")
    print("="*40)
    
    print("Pilih sumber target keyword:")
    print("1. Ketik manual (Satu keyword)")
    print("2. Ambil dari file 'keywords.txt' (Banyak keyword)")
    sumber = input("Masukkan pilihan (1/2): ")

    print("\nPilih rute scraping:")
    print("1. Metode /find (Aman & Stabil)")
    print("2. Metode /search (Rawan Blokir)")
    metode = input("Masukkan pilihan (1/2): ")

    if sumber == "1":
        keyword = input("\nMasukkan keyword produk: ")
        if metode == "1":
            await scrape_find_page(keyword, max_pages=1)
        elif metode == "2":
            await scrape_search_page(keyword)
    elif sumber == "2":
        # Memanggil fungsi baca file di atas
        await process_from_file("keywords.txt", metode)
    else:
        print("[!] Pilihan sumber tidak valid.")

if __name__ == "__main__":
    asyncio.run(main())