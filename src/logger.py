import os
from datetime import datetime
from typing import Optional


class ScraperLogger:
    """Logger untuk scraping dengan format one-liner.

    Output:
    - Console: print langsung
    - File: logs/{log_type}/YYYY-MM-DD.log
    """

    def __init__(self, log_type: str = "search"):
        self.log_type = log_type
        self.log_dir = f"logs/{log_type}"
        os.makedirs(self.log_dir, exist_ok=True)

        # File log harian
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_file = f"{self.log_dir}/{today}.log"

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _write(self, message: str):
        """Write ke file log dan print ke console."""
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(f"[{self._timestamp()}] {message}\n")
        print(message)

    def info(self, message: str):
        """Log informasi umum."""
        self._write(message)

    def keyword_result(
        self,
        index: str,
        keyword: str,
        count: int,
        new: int,
        updated: int,
        duration: float,
        mode: str,
        error: Optional[str] = None
    ):
        """One-liner untuk hasil scraping per keyword.

        Format:
        ✅ [1/38] 'macbook m1 pro' → 120 (85+35) ⏱️15.2s 🟢UI
        ❌ [4/38] 'jam rolex' → 0 (0+0) ⏱️8.1s ⚫ [CAPTCHA_BLOCK]
        """
        icon = "✅" if error is None else "❌"
        mode_icon = "🟢UI" if mode == "HEADFUL" else "⚫"
        error_text = f" [{error}]" if error else ""

        msg = f"{icon} [{index}] '{keyword}' → {count} ({new}+{updated}) ⏱️{duration:.1f}s {mode_icon}{error_text}"
        self._write(msg)

    def batch_start(
        self,
        marketplace: str,
        total: int,
        pending: int,
        skipped: int,
        mode: str
    ):
        """Log awal batch processing.

        Format:
        🚀 SHOPEE BATCH START | Total: 50 | Pending: 38 | Skipped: 12 | Mode: HEAD-2
        """
        msg = f"🚀 {marketplace.upper()} BATCH START | Total: {total} | Pending: {pending} | Skipped: {skipped} | Mode: {mode}"
        self._write(msg)

    def batch_end(
        self,
        completed: int,
        success: int,
        failed: int,
        total_products: int,
        duration: float
    ):
        """Log akhir batch processing.

        Format:
        📊 BATCH END | Completed: 38 | ✅37 | ❌1 | 📦3420 | ⏱️915s
        """
        msg = f"📊 BATCH END | Completed: {completed} | ✅{success} | ❌{failed} | 📦{total_products} | ⏱️{duration:.0f}s"
        self._write(msg)

    def single_start(self, marketplace: str, keyword: str, mode: str):
        """Log awal single keyword search.

        Format:
        🚀 TOKOPEDIA SINGLE 'macbook m1 pro' | Mode: HEADLESS
        """
        msg = f"🚀 {marketplace.upper()} SINGLE '{keyword}' | Mode: {mode}"
        self._write(msg)

    def single_end(
        self,
        keyword: str,
        count: int,
        new: int,
        updated: int,
        duration: float,
        mode: str,
        error: Optional[str] = None
    ):
        """Log akhir single keyword search.

        Format:
        ✅ SINGLE 'macbook m1 pro' → 120 (85+35) ⏱️15.2s 🟢UI
        ❌ SINGLE 'jam rolex' → 0 (0+0) ⏱️8.1s ⚫ [CAPTCHA_BLOCK]
        """
        icon = "✅" if error is None else "❌"
        mode_icon = "🟢UI" if mode == "HEADFUL" else "⚫"
        error_text = f" [{error}]" if error else ""

        msg = f"{icon} SINGLE '{keyword}' → {count} ({new}+{updated}) ⏱️{duration:.1f}s {mode_icon}{error_text}"
        self._write(msg)
