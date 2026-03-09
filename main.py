import asyncio
import argparse
import os
from typing import List

from src.scrapers.tokopedia.scraper_find import scrape_find_page
from src.scrapers.tokopedia.scraper_search import scrape_search_page
from src.database import db


async def process_from_file(filename: str, method: str) -> None:
    if not os.path.exists(filename):
        print(f"\n[!] Error: File '{filename}' tidak ditemukan.")
        return

    with open(filename, "r", encoding="utf-8") as f:
        keywords: List[str] = [line.strip() for line in f.readlines() if line.strip()]

    if not keywords:
        print(f"\n[!] File '{filename}' kosong.")
        return

    print(
        f"\n[*] Ditemukan {len(keywords)} target di '{filename}'. Memulai proses batch..."
    )

    for index, keyword in enumerate(keywords, start=1):
        print(f"\n{'-'*30}\nMemproses [{index}/{len(keywords)}]: {keyword}\n{'-'*30}")

        if method == "find":
            await scrape_find_page(keyword)
        elif method == "search":
            await scrape_search_page(keyword)

        if index < len(keywords):
            print(f"[*] Jeda 5 detik sebelum keyword berikutnya...")
            await asyncio.sleep(5)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-Marketplace Scraper CLI")
    parser.add_argument(
        "-k", "--keyword", type=str, help="Satu keyword spesifik (contoh: tenda)"
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        default="keywords.txt",
        help="File target (default: keywords.txt)",
    )
    parser.add_argument(
        "-m",
        "--method",
        type=str,
        choices=["find", "search"],
        default="find",
        help="Metode scraping (Default: find)",
    )

    args = parser.parse_args()

    print("=" * 40)
    print("🤖 E-COMMERCE SCRAPER BOT")
    print("=" * 40)
    print(f"[*] Metode aktif: /{args.method}\n")

    try:
        if args.keyword:
            print(f"[*] Menjalankan mode Single Keyword: '{args.keyword}'")
            if args.method == "find":
                await scrape_find_page(args.keyword)
            elif args.method == "search":
                await scrape_search_page(args.keyword)
        else:
            print(f"[*] Mode Batch. Membaca dari file: {args.file}")
            await process_from_file(args.file, args.method)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
