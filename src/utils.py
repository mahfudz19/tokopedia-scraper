import json
import os
import hashlib
import requests
import boto3

from typing import List, Dict, Any
from playwright.async_api import Page
from botocore.exceptions import  ClientError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from botocore.exceptions import BotoCoreError, ClientError

# =========================================================================
# OPTIMASI 1: GLOBAL SESSION & AUTO-RETRY
# Mencegah ConnectionResetError(54) dengan mendaur ulang koneksi (Keep-Alive)
# dan otomatis mencoba ulang jika server memutus koneksi tiba-tiba.
# =========================================================================
http_session = requests.Session()
retry_strategy = Retry(
    total=3,                # Maksimal coba 3 kali jika gagal
    backoff_factor=1,       # Jeda eksponensial: 1 detik, 2 detik, 4 detik...
    status_forcelist=[429, 500, 502, 503, 504], # Coba lagi jika server sibuk/error
    allowed_methods=["HEAD", "GET", "OPTIONS"]  # Berlaku untuk method ini
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http_session.mount("http://", adapter)
http_session.mount("https://", adapter)

# Simpan S3 Client secara global agar tidak buka-tutup koneksi AWS terus menerus
s3_client_global = None

def get_s3_client():
    global s3_client_global
    if s3_client_global is None:
        bucket_name = os.getenv('AWS_BUCKET_NAME')
        region = os.getenv('AWS_BUCKET_REGION')
        access_key = os.getenv('AWS_ACCESS_KEY')
        secret_key = os.getenv('AWS_SECRET_KEY')

        if all([bucket_name, region, access_key, secret_key]):
            s3_client_global = boto3.client(
                's3',
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
    return s3_client_global


def upload_image_to_s3(image_url: str) -> str:
    """
    Mendownload gambar dari URL dan mengunggahnya ke AWS S3.
    Mencegah duplikasi dengan menggunakan MD5 Hash dari URL asli.
    """
    if not image_url:
        return None

    # Bungkus seluruh fungsi dalam Try-Except agar error fatal jaringan (seperti Error 54)
    # tidak membuat bot / main.py mati (crash).
    try:
        bucket_name = os.getenv('AWS_BUCKET_NAME')
        region = os.getenv('AWS_BUCKET_REGION')
        s3_client = get_s3_client()

        if not s3_client:
            print("❌ Konfigurasi AWS S3 tidak lengkap di file .env")
            return None

        # 1. Buat Nama File Deterministik menggunakan MD5 Hash dari URL asli
        ext = image_url.split('.')[-1].split('?')[0]
        if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp']:
            ext = 'jpg'
            
        url_hash = hashlib.md5(image_url.encode('utf-8')).hexdigest()
        file_name = f"products/{url_hash}.{ext}"
        s3_url = file_name

        # 2. Cek apakah file sudah ada di S3 (Super Cepat)
        try:
            s3_client.head_object(Bucket=bucket_name, Key=file_name)
            return s3_url # Langsung kembalikan URL jika gambar sudah ada
        except ClientError as e:
            if e.response['Error']['Code'] != '404':
                pass # Lanjut download jika error lain

        # 3. Download gambar menggunakan Global Session (Anti Connection Reset)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Connection': 'keep-alive'
        }
        
        # timeout=(connect timeout, read timeout)
        response = http_session.get(image_url, headers=headers, stream=True, timeout=(5, 15))
        response.raise_for_status() 

        content_type = response.headers.get('Content-Type', 'image/jpeg')

        # 4. Upload ke AWS S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=response.content,
            ContentType=content_type,
        )
        return s3_url
        
    except requests.exceptions.RequestException as e:
        # Menangani khusus error download / Connection Reset
        print(f"⚠️ Gagal download gambar (Jaringan terputus): {str(e)[:50]}...")
        return None
    except Exception as e:
        # Menangani error tak terduga lainnya agar bot tidak crash
        print(f"⚠️ Gagal memproses S3 untuk gambar ini: {str(e)[:50]}...")
        return None

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
        json.dump(data, f, ensure_ascii=False, indent=4, default=str)

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
