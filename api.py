from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

# Import fungsi scraper dari kode Anda
from src.scrapers.tokopedia.scraper_find import scrape_find_page
from src.scrapers.lazada.scraper_tag import scrape_lazada_tag
from src.scrapers.shopee.scraper_search import scrape_shopee_search

app = FastAPI(title="Scraper API with noVNC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Mengizinkan semua origin (Bisa diganti domain frontend Anda nanti)
    allow_credentials=True,
    allow_methods=["*"], # Mengizinkan POST, GET, dll
    allow_headers=["*"],
)

# Format request JSON yang diterima
class ScrapeRequest(BaseModel):
    keyword: str
    method: str = "shopee"
    head_limit: int = 0  # Jika > 0, jalankan browser dengan UI terbuka

@app.post("/scrape")
async def start_scraping(req: ScrapeRequest, background_tasks: BackgroundTasks):
    show_head = req.head_limit > 0
    
    # Fungsi pembungkus untuk dijalankan di background agar API langsung merespons
    async def run_scraper():
        print(f"[*] API MEMULAI SCRAPING: {req.keyword} | Metode: {req.method} | Head: {show_head}")
        try:
            if req.method == "tokopedia":
                await scrape_find_page(req.keyword, show_head)
            elif req.method == "lazada":
                await scrape_lazada_tag(req.keyword, show_head)
            elif req.method == "shopee":
                await scrape_shopee_search(req.keyword, show_head)
        except Exception as e:
            print(f"[!] ERROR API SCRAPER: {e}")

    # Masukkan ke antrean background
    background_tasks.add_task(run_scraper)
    
    return {
        "success": True,
        "message": f"Tugas scraping '{req.keyword}' ditambahkan ke antrean.",
        "mode": "HEADFUL (UI)" if show_head else "HEADLESS (Background)"
    }

@app.get("/")
def health_check():
    return {"status": "ok", "service": "Scraper API is running!"}