import os
from datetime import datetime, timezone
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

        self.db: MongoDatabase = self.client["scraper"]
        self.products_collection: Collection = self.db["products"]

        # Membuat unique index
        self.products_collection.create_index("url", unique=True)
        self.products_collection.create_index("category")
        self.products_collection.create_index("marketplace_product_id", unique=True)
        
        # Compound index untuk query yang sering digunakan bersamaan
        self.products_collection.create_index([("category", 1), ("marketplace", 1)])
        print("✓ Terhubung ke Database MongoDB: scraper (Index aktif: url, category, marketplace_product_id)")

    def insert_products(
        self, products_list: List[Dict[str, Any]], source_marketplace: str
    ) -> None:
        """Melakukan Upsert data produk ke MongoDB dengan Timestamp."""
        if not products_list:
            print(f"[-] Tidak ada data dari {source_marketplace} untuk disimpan ke DB.")
            return

        operations: List[UpdateOne] = []

        # 2. Ambil waktu saat ini berstandar UTC
        current_time = datetime.now(timezone.utc)

        for product in products_list:
            product["marketplace"] = source_marketplace

            # 3. Selalu perbarui updatedAt setiap kali produk ini di-scrape ulang
            product["updatedAt"] = current_time

            op = UpdateOne(
                filter={"url": product["url"]},
                update={
                    "$set": product,
                    # 4. createdAt HANYA diisi jika produk ini benar-benar baru di DB
                    "$setOnInsert": {"createdAt": current_time},
                },
                upsert=True,
            )
            operations.append(op)

        try:
            result = self.products_collection.bulk_write(operations)
            print(
                f"[v] Laporan MongoDB ({source_marketplace}): Baru={result.upserted_count}, Diperbarui={result.modified_count}"
            )
        except Exception as e:
            print(f"[!] Gagal menyimpan ke database: {e}")

    def close(self) -> None:
        self.client.close()
        print("✓ Koneksi database ditutup.")


db = Database()
