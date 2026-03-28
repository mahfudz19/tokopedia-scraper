import asyncio
import argparse
import os
from typing import List

from src.scrapers.tokopedia.scraper_find import scrape_find_page
from src.scrapers.lazada.scraper_tag import scrape_lazada_tag
from src.scrapers.shopee.scraper_search import scrape_shopee_search
from src.database import db


async def process_from_file(filename: str, method: str, show_head: bool) -> None:
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

    print(f"\n[*] Ditemukan {len(keywords)} target total.")
    print(
        f"[*] {len(completed_keywords)} sudah selesai. Menyisakan {len(pending_keywords)} target untuk diproses..."
    )

    for index, keyword in enumerate(pending_keywords, start=1):
        print(
            f"\n{'-'*30}\nMemproses [{index}/{len(pending_keywords)}]: {keyword}\n{'-'*30}"
        )

        try:
            # Jalankan Scraper
            if method == "tokopedia":
                await scrape_find_page(keyword, show_head)
            elif method == "lazada":
                await scrape_lazada_tag(keyword, show_head)
            elif method == "shopee":
                await scrape_shopee_search(keyword, show_head)

            # Jika berhasil (tidak ada error), catat keyword ini ke dalam daftar "SUKSES"
            with open(completed_file, "a", encoding="utf-8") as f:
                f.write(keyword + "\n")

        # ==========================================
        # --- BEHAVIOR 1: CIRCUIT BREAKER CATCHER ---
        # ==========================================
        except RuntimeError as e:
            if str(e) == "CAPTCHA_BLOCK":
                print("\n" + "!" * 50)
                print("[!!!] CIRCUIT BREAKER AKTIF: PROSES BATCH DIHENTIKAN [!!!]")
                print("!" * 50)
                print(
                    "Alasan   : Datadome mendeteksi bot dan meminta penyelesaian CAPTCHA."
                )
                print(
                    "Tindakan : Skrip dihentikan seketika untuk mencegah Banned IP/Profil."
                )
                print(
                    f"Status   : Sisa {len(pending_keywords) - index + 1} keyword aman tersimpan di antrean."
                )
                print("!" * 50 + "\n")
                break  # Hentikan paksa loop FOR ini, jangan lanjut ke keyword berikutnya!
            else:
                # Jika error lain, biarkan lanjut
                print(f"[!] Terjadi error tidak terduga: {e}")

        if index < len(pending_keywords):
            print(f"[*] Jeda 2 detik sebelum keyword berikutnya...")
            await asyncio.sleep(2)


async def main() -> None:
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
    parser.add_argument(
        "--head",
        action="store_true",
        help="Tampilkan UI browser (Mode Headful) untuk solve CAPTCHA/Login",
    )

    args = parser.parse_args()

    print("=" * 40)
    print("🤖 E-COMMERCE SCRAPER BOT")
    print("=" * 40)
    print(f"[*] Metode aktif: /{args.method}\n")

    try:
        if args.keyword:
            print(f"[*] Menjalankan mode Single Keyword: '{args.keyword}'")
            if args.method == "tokopedia":
                await scrape_find_page(args.keyword, args.head)
            elif args.method == "lazada":
                await scrape_lazada_tag(args.keyword, args.head)
            elif args.method == "shopee":
                await scrape_shopee_search(args.keyword, args.head)
        else:
            print(f"[*] Mode Batch. Membaca dari file: {args.file}")
            await process_from_file(args.file, args.method, args.head)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
