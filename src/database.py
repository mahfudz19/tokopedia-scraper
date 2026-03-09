import os
from pymongo import MongoClient, UpdateOne
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.mongo_uri = os.getenv("MONGODB_URI")
        if not self.mongo_uri:
            raise ValueError("[!] MONGODB_URI tidak ditemukan di file .env")
        
        print("[*] Menghubungkan ke MongoDB...")
        self.client = MongoClient(self.mongo_uri)
        
        # Sesuai URL kamu, nama databasenya adalah 'scraper'
        self.db = self.client['scraper']
        self.products_collection = self.db['products']
        
        # --- PEMBUATAN INDEX OTOMATIS ---
        # Mirip dengan Mongoose, kita pastikan ada unique index pada field 'url'.
        # Jika index sudah ada di database, MongoDB akan mengabaikan perintah ini secara otomatis.
        self.products_collection.create_index("url", unique=True)
        
        print("✓ Terhubung ke Database MongoDB: scraper (Index unik pada 'url' aktif)")

    def insert_products(self, products_list, source_marketplace):
        """
        Menyimpan banyak produk menggunakan mekanisme UPSERT.
        Mencegah duplikasi data berdasarkan URL.
        """
        if not products_list:
            print(f"[-] Tidak ada data dari {source_marketplace} untuk disimpan.")
            return

        operations = []
        for product in products_list:
            product['marketplace'] = source_marketplace
            
            # --- MEKANISME UPSERT (Update / Insert) ---
            # Cari berdasarkan 'url'. Jika ketemu, timpa (update) dengan data scraping terbaru.
            # Jika belum ketemu, masukkan sebagai dokumen baru (insert).
            op = UpdateOne(
                filter={'url': product['url']}, 
                update={'$set': product},        
                upsert=True                      
            )
            operations.append(op)

        try:
            # Mengeksekusi semua operasi sekalian (Bulk Write) agar sangat cepat
            result = self.products_collection.bulk_write(operations)
            print(f"[v] Laporan Penyimpanan ke Database ({source_marketplace}):")
            print(f"    - Produk Baru (Inserted) : {result.upserted_count}")
            print(f"    - Produk Lama (Updated)  : {result.modified_count}")
        except Exception as e:
            print(f"[!] Gagal menyimpan ke database: {e}")

    def close(self):
        self.client.close()
        print("✓ Koneksi database ditutup.")

# Inisialisasi object agar bisa di-import langsung oleh scraper lain
db = Database()