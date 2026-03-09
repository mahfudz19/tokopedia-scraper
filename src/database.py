import os
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

load_dotenv()

class Database:
    def __init__(self) -> None:
        self.mongo_uri: Optional[str] = os.getenv("MONGODB_URI")
        if not self.mongo_uri:
            raise ValueError("[!] MONGODB_URI tidak ditemukan di file .env")
        
        print("[*] Menghubungkan ke MongoDB...")
        self.client: MongoClient = MongoClient(self.mongo_uri)
        
        self.db: MongoDatabase = self.client['scraper']
        self.products_collection: Collection = self.db['products']
        
        # Membuat unique index
        self.products_collection.create_index("url", unique=True)
        print("✓ Terhubung ke Database MongoDB: scraper (Index unik pada 'url' aktif)")

    def insert_products(self, products_list: List[Dict[str, Any]], source_marketplace: str) -> None:
        """Melakukan Upsert data produk ke MongoDB."""
        if not products_list:
            print(f"[-] Tidak ada data dari {source_marketplace} untuk disimpan ke DB.")
            return

        operations: List[UpdateOne] = []
        for product in products_list:
            product['marketplace'] = source_marketplace
            op = UpdateOne(
                filter={'url': product['url']}, 
                update={'$set': product},        
                upsert=True                      
            )
            operations.append(op)

        try:
            result = self.products_collection.bulk_write(operations)
            print(f"[v] Laporan MongoDB ({source_marketplace}): Baru={result.upserted_count}, Diperbarui={result.modified_count}")
        except Exception as e:
            print(f"[!] Gagal menyimpan ke database: {e}")

    def close(self) -> None:
        self.client.close()
        print("✓ Koneksi database ditutup.")

db = Database()