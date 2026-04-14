import asyncio
import argparse
import os
import sys
import re
from typing import List

from src.scrapers.tokopedia.scraper_find import scrape_find_page
from src.scrapers.lazada.scraper_tag import scrape_lazada_tag
from src.scrapers.shopee.scraper_search import scrape_shopee_search
from src.database import db

async def process_from_file(filename: str, method: str, head_limit: float) -> None:
    if not os.path.exists(filename):
        print(f"\n[!] Error: File '{filename}' tidak ditemukan.")
        return

    with open(filename, "r", encoding="utf-8") as f:
        keywords: List[str] = [line.strip() for line in f.readlines() if line.strip()]

    if not keywords:
        print(f"\n[!] File '{filename}' kosong.")
        return

    completed_file = f"completed_{method}.txt"
    completed_keywords = set()

    # Baca keyword apa saja yang sudah sukses di masa lalu
    if os.path.exists(completed_file):
        with open(completed_file, "r", encoding="utf-8") as f:
            completed_keywords = set(
                line.strip() for line in f.readlines() if line.strip()
            )

    # Saring keyword, hanya ambil yang BELUM ada di file completed
    pending_keywords = [k for k in keywords if k not in completed_keywords]

    if not pending_keywords:
        print(
            f"\n[✓] Luar biasa! Semua target di '{filename}' sudah selesai dikerjakan sebelumnya."
        )
        return

    print(f"\n[*] Menemukan {len(pending_keywords)} keyword yang belum diproses.")

    for idx, kw in enumerate(pending_keywords):
        print(f"\n========================================")
        print(f"[{idx+1}/{len(pending_keywords)}] Memproses keyword: '{kw}'")
        print(f"========================================")

        # LOGIKA FLAG DINAMIS: True jika indeks saat ini di bawah limit head
        show_head = idx < head_limit

        if method == "tokopedia":
            await scrape_find_page(kw, show_head)
        elif method == "lazada":
            await scrape_lazada_tag(kw, show_head)
        elif method == "shopee":
            await scrape_shopee_search(kw, show_head)

        # Catat ke file completed setelah berhasil (untuk resume jika crash)
        with open(completed_file, "a", encoding="utf-8") as f:
            f.write(kw + "\n")

        # Jeda antar keyword agar tidak terlalu dicurigai sebagai DDoS
        if idx < len(pending_keywords) - 1:
            print("\n[*] Jeda 2 detik sebelum keyword berikutnya...")
            await asyncio.sleep(2)


async def main() -> None:
    # -------------------------------------------------------------
    # CUSTOM ARGUMENT PARSING UNTUK FLAG DINAMIS (--head-X)
    # -------------------------------------------------------------
    head_limit = 0
    args_to_parse = []
    
    for arg in sys.argv:
        if arg == "--head":
            # Jika hanya '--head', maka buka UI untuk SEMUA iterasi
            head_limit = float('inf')
        elif re.match(r"--head-(\d+)", arg):
            # Jika '--head-X', maka buka UI hanya untuk X iterasi pertama
            match = re.match(r"--head-(\d+)", arg)
            head_limit = int(match.group(1))
        else:
            args_to_parse.append(arg)
            
    # Timpa sys.argv agar argparse tidak error karena ada argumen yang tidak dikenal
    sys.argv = args_to_parse
    # -------------------------------------------------------------

    parser = argparse.ArgumentParser(description="Multi-Marketplace Scraper CLI")
    parser.add_argument("-k", "--keyword", type=str, help="Satu keyword spesifik")
    parser.add_argument(
        "-f", "--file", type=str, default="keywords.txt", help="File target"
    )
    parser.add_argument(
        "-m",
        "--method",
        type=str,
        choices=["tokopedia", "shopee", "lazada"],
        default="shopee",
        help="Metode scraping",
    )
    
    # Keterangan manual karena argumen '--head' sudah kita bypass di atas
    parser.epilog = "Contoh Flag UI Tambahan:\n  --head        Buka browser (UI) untuk semua antrean\n  --head-N      Buka browser (UI) HANYA untuk N antrean pertama (misal: --head-2)"

    args = parser.parse_args()

    print("=" * 40)
    print("🤖 E-COMMERCE SCRAPER BOT")
    print("=" * 40)
    print(f"[*] Metode aktif: /{args.method}\n")

    try:
        if args.keyword:
            print(f"[*] Menjalankan mode Single Keyword: '{args.keyword}'")
            # Untuk single keyword, show_head bernilai True asalkan limit > 0
            show_head = head_limit > 0 
            if args.method == "tokopedia":
                await scrape_find_page(args.keyword, show_head)
            elif args.method == "lazada":
                await scrape_lazada_tag(args.keyword, show_head)
            elif args.method == "shopee":
                await scrape_shopee_search(args.keyword, show_head)
        else:
            print(f"[*] Menjalankan mode File: {args.file}")
            await process_from_file(args.file, args.method, head_limit)

    except KeyboardInterrupt:
        print("\n[!] Proses dihentikan paksa oleh pengguna (Ctrl+C).")
    except Exception as e:
        print(f"\n[!] Terjadi kesalahan tak terduga: {e}")
    finally:
        print("✓ Koneksi database ditutup.")


if __name__ == "__main__":
    asyncio.run(main())