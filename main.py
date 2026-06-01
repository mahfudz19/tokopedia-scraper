import asyncio
import argparse
import os
import sys
import re
import time
from typing import List, Dict, Any

from src.scrapers.tokopedia.scraper_find import scrape_find_page
from src.scrapers.lazada.scraper_tag import scrape_lazada_tag
from src.scrapers.shopee.scraper_search import scrape_shopee_search
from src.database import db
from src.logger import ScraperLogger

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

    # Setup logger
    logger = ScraperLogger(log_type="search")

    # Tentukan mode text
    if head_limit == float('inf'):
        mode_text = "HEADFUL"
    elif head_limit > 0:
        mode_text = f"HEAD-{int(head_limit)}"
    else:
        mode_text = "HEADLESS"

    # Log batch start
    logger.batch_start(method, len(keywords), len(pending_keywords), len(completed_keywords), mode_text)

    # Track results untuk summary
    results: List[Dict[str, Any]] = []
    batch_start_time = time.time()

    for idx, kw in enumerate(pending_keywords):
        keyword_start_time = time.time()

        # LOGIKA FLAG DINAMIS: True jika indeks saat ini di bawah limit head
        show_head = idx < head_limit
        current_mode = "HEADFUL" if show_head else "HEADLESS"

        try:
            # Call scraper dan dapatkan metadata
            if method == "tokopedia":
                result = await scrape_find_page(kw, show_head)
            elif method == "lazada":
                result = await scrape_lazada_tag(kw, show_head)
            elif method == "shopee":
                result = await scrape_shopee_search(kw, show_head)

            duration = time.time() - keyword_start_time

            # Extract metadata dari result
            products_count = result.get("products_count", 0) if result else 0
            db_new = result.get("db_new", 0) if result else 0
            db_updated = result.get("db_updated", 0) if result else 0

            logger.keyword_result(
                index=f"{idx+1}/{len(pending_keywords)}",
                keyword=kw,
                count=products_count,
                new=db_new,
                updated=db_updated,
                duration=duration,
                mode=current_mode
            )
            results.append({"keyword": kw, "success": True, "count": products_count, "error": None})

        except Exception as e:
            duration = time.time() - keyword_start_time
            error_msg = str(e)[:50]  # Truncate error message
            logger.keyword_result(
                index=f"{idx+1}/{len(pending_keywords)}",
                keyword=kw,
                count=0,
                new=0,
                updated=0,
                duration=duration,
                mode=current_mode,
                error=error_msg
            )
            results.append({"keyword": kw, "success": False, "count": 0, "error": str(e)})

        # Catat ke file completed setelah selesai (untuk resume jika crash)
        with open(completed_file, "a", encoding="utf-8") as f:
            f.write(kw + "\n")

        # Jeda antar keyword agar tidak terlalu dicurigai sebagai DDoS
        if idx < len(pending_keywords) - 1:
            await asyncio.sleep(2)

    # Log batch end
    batch_duration = time.time() - batch_start_time
    success_count = sum(1 for r in results if r["success"])
    failed_count = len(results) - success_count
    total_products = sum(r["count"] for r in results)

    logger.batch_end(
        completed=len(pending_keywords),
        success=success_count,
        failed=failed_count,
        total_products=total_products,
        duration=batch_duration
    )


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


    try:
        if args.keyword:
            # Setup logger
            logger = ScraperLogger(log_type="search")

            # Tentukan mode
            show_head = head_limit > 0
            mode_text = "HEADFUL" if show_head else "HEADLESS"

            # Log single start
            logger.single_start(args.method, args.keyword, mode_text)

            keyword_start_time = time.time()

            # Call scraper dan dapatkan metadata
            if args.method == "tokopedia":
                result = await scrape_find_page(args.keyword, show_head)
            elif args.method == "lazada":
                result = await scrape_lazada_tag(args.keyword, show_head)
            elif args.method == "shopee":
                result = await scrape_shopee_search(args.keyword, show_head)

            duration = time.time() - keyword_start_time

            # Extract metadata dari result
            products_count = result.get("products_count", 0) if result else 0
            db_new = result.get("db_new", 0) if result else 0
            db_updated = result.get("db_updated", 0) if result else 0

            logger.single_end(
                keyword=args.keyword,
                count=products_count,
                new=db_new,
                updated=db_updated,
                duration=duration,
                mode=mode_text
            )
        else:
            await process_from_file(args.file, args.method, head_limit)

    except KeyboardInterrupt:
        print("\n[!] Proses dihentikan paksa oleh pengguna (Ctrl+C).")
    except Exception as e:
        print(f"\n[!] Terjadi kesalahan tak terduga: {e}")


if __name__ == "__main__":
    asyncio.run(main())