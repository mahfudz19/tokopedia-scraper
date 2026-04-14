# test_s3.py
from dotenv import load_dotenv
from src.utils import upload_image_to_s3

# Load konfigurasi dari .env
load_dotenv()

def test():
    print("Mulai proses testing download & upload ke S3...")
    
    # URL testing yang Anda berikan
    test_url = "https://p16-images-sign-sg.tokopedia-static.net/tos-alisg-i-aphluv4xwc-sg/24a7fcb85eb746ee971cc876b9c3d286~tplv-aphluv4xwc-white-pad-v1:200:200.jpeg?lk3s=97278606&x-expires=1776175247&x-signature=CpjOfyyLwDTVmvEcH8cnakhxYXQ%3D&x-signature-webp=dHeVjXAUA9yprBxV%2Fx0RsFv2cVw%3D"
    
    result_url = upload_image_to_s3(test_url)
    
    if result_url:
        print(f"\n✅ SUKSES! Gambar berhasil disimpan di: \n{result_url}")
        print("Silakan klik link di atas untuk memastikannya bisa dibuka di browser.")
    else:
        print("\n❌ GAGAL! Silakan cek pesan error di atas.")

if __name__ == "__main__":
    test()