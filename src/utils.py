import json
import os
import hashlib
import requests
import boto3

from typing import List, Dict, Any
from playwright.async_api import Page, Locator
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime

def upload_image_to_s3(image_url: str) -> str:
    """
    Mendownload gambar dari URL dan mengunggahnya ke AWS S3.
    Mencegah duplikasi dengan menggunakan MD5 Hash dari URL asli.
    """
    if not image_url:
        return None

    # 1. Ambil konfigurasi AWS
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    region = os.getenv('AWS_BUCKET_REGION')
    access_key = os.getenv('AWS_ACCESS_KEY')
    secret_key = os.getenv('AWS_SECRET_KEY')

    if not all([bucket_name, region, access_key, secret_key]):
        print("❌ Konfigurasi AWS S3 tidak lengkap di file .env")
        return None

    # 2. Setup client AWS S3
    s3_client = boto3.client(
        's3',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    # 3. Buat Nama File Deterministik menggunakan MD5 Hash dari URL asli
    # Ekstrak ekstensi kasar (default ke jpg jika sulit ditebak)
    ext = image_url.split('.')[-1].split('?')[0]
    if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp']:
        ext = 'jpg'
        
    url_hash = hashlib.md5(image_url.encode('utf-8')).hexdigest()
    file_name = f"products/{url_hash}.{ext}"
    s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_name}"

    # =========================================================
    # OPTIMASI SUPER CEPAT: Cek apakah file sudah ada di S3
    # =========================================================
    try:
        # head_object sangat ringan dan cepat, hanya mengecek metadata file
        s3_client.head_object(Bucket=bucket_name, Key=file_name)
        # Jika tidak error, berarti file sudah ada! Langsung kembalikan URL S3
        return s3_url
    except ClientError as e:
        # Error 404 berarti file belum ada (Not Found), kita lanjut download & upload
        if e.response['Error']['Code'] != '404':
            print(f"⚠️ Peringatan saat mengecek S3: {e}")
            # Lanjut saja jika error lain

    # 4. Download gambar jika belum ada di S3
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(image_url, headers=headers, stream=True, timeout=15)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mendownload gambar: {e}")
        return None

    content_type = response.headers.get('Content-Type', 'image/jpeg')

    # 5. Upload ke AWS S3 (Jika ada file lama yang sama secara kebetulan, ini akan Overwrite)
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=response.content,
            ContentType=content_type,
        )
        return s3_url
        
    except (BotoCoreError, ClientError) as e:
        print(f"❌ Gagal mengunggah ke S3: {e}")
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
