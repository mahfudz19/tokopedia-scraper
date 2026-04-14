import json
import os
import uuid
import requests
import boto3

from typing import List, Dict, Any
from playwright.async_api import Page, Locator
from botocore.exceptions import BotoCoreError, ClientError
from datetime import datetime

def upload_image_to_s3(image_url: str) -> str:
    """
    Mendownload gambar dari URL dan mengunggahnya ke AWS S3.
    Mengembalikan URL gambar di S3 jika berhasil, atau None jika gagal.
    """
    if not image_url:
        return None

    # 1. Coba download gambar dari URL target
    try:
        # Menambahkan User-Agent penting agar request tidak diblokir oleh Tokopedia/Shopee
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(image_url, headers=headers, stream=True, timeout=15)
        
        # Raise exception jika status code bukan 200 (OK)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"❌ Gagal mendownload gambar: {e}")
        return None

    # 2. Ambil konfigurasi AWS dari environment variables
    bucket_name = os.getenv('AWS_BUCKET_NAME')
    region = os.getenv('AWS_BUCKET_REGION')
    access_key = os.getenv('AWS_ACCESS_KEY')
    secret_key = os.getenv('AWS_SECRET_KEY')

    if not all([bucket_name, region, access_key, secret_key]):
        print("❌ Konfigurasi AWS S3 tidak lengkap di file .env")
        return None

    # 3. Setup client AWS S3
    s3_client = boto3.client(
        's3',
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key
    )

    # 4. Ekstrak Content-Type untuk ekstensi file yang valid (default ke jpg)
    content_type = response.headers.get('Content-Type', 'image/jpeg')
    ext = content_type.split('/')[-1] if '/' in content_type else 'jpg'
    if ext == 'jpeg': 
        ext = 'jpg'
        
    # Generate nama file unik, misalnya: products/{year}/{mounth}/{date}/a1b2c3d4.jpg
    now = datetime.now()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    date = now.strftime("%d")
    file_name = f"products/{year}/{month}/{date}/{uuid.uuid4().hex}.{ext}"

    # 5. Upload ke AWS S3
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_name,
            Body=response.content,
            ContentType=content_type,
            # ACL='public-read' # Buka komentar (uncomment) baris ini jika bucket Anda memblokir public access dan Anda ingin gambar ini public
        )
        
        # 6. Konstruksi URL S3 hasil upload
        s3_url = f"{file_name}"
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
