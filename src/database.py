import os
import dns.resolver
from datetime import datetime, timezone
from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection
from pymongo.database import Database as MongoDatabase
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

load_dotenv()

dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']

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
        
        # Index untuk query yang sering digunakan
        self.products_collection.create_index("marketplace")
        self.products_collection.create_index("search_keyword")
        
        print("✓ Terhubung ke Database MongoDB: scraper (Index aktif: url, marketplace, search_keyword)")

    def insert_products(
        self, products_list: List[Dict[str, Any]], source_marketplace: str, search_keyword: Optional[str] = None
    ) -> None:
        """Melakukan Upsert data produk ke MongoDB dengan Timestamp dan validasi field wajib.
        
        Args:
            products_list: List produk yang akan disimpan
            source_marketplace: Nama marketplace sumber (shopee, tokopedia, lazada)
            search_keyword: Keyword pencarian yang digunakan untuk scraping
        
        Raises:
            ValueError: Jika field wajib tidak ada atau kosong
        """
        # Field wajib yang harus ada di setiap produk
        REQUIRED_FIELDS = {'url', 'location', 'name', 'price_rp'}
        
        if not products_list:
            print(f"[-] Tidak ada data dari {source_marketplace} untuk disimpan ke DB.")
            return

        operations: List[UpdateOne] = []
        skipped_count = 0

        # Ambil waktu saat ini berstandar UTC
        current_time = datetime.now(timezone.utc)

        for idx, product in enumerate(products_list):
            # 1. Validasi field wajib - kumpulkan field yang hilang atau kosong
            missing_fields = []
            invalid_fields = []
            
            for field in REQUIRED_FIELDS:
                if field not in product:
                    missing_fields.append(field)
                elif product[field] is None or product[field] == '':
                    invalid_fields.append(field)
            
            # Throw error jika ada field wajib yang hilang atau kosong
            if missing_fields:
                print(f"[!] Skip produk #{idx + 1} ({source_marketplace}): Field wajib kosong: {', '.join(missing_fields)}")
                skipped_count += 1
                continue
            
            if invalid_fields:
                print(f"[!] Skip produk #{idx + 1} ({source_marketplace}): Field wajib tidak valid: {', '.join(invalid_fields)}")
                skipped_count += 1
                continue
            
            # Validasi tambahan untuk field bertipe int (price_rp)
            if not isinstance(product.get('price_rp'), (int, float)):
                print(f"[!] Skip produk #{idx + 1} ({source_marketplace}): price_rp harus bertipe integer, ditemukan: {type(product.get('price_rp'))}")
                skipped_count += 1
                continue
            
            # 2. Filter produk - hanya ambil field yang diperlukan
            clean_product = {
                'url': str(product['url']).strip(),
                'location': str(product['location']).strip(),
                'marketplace': source_marketplace,
                'name': str(product['name']).strip(),
                'price_rp': int(product['price_rp']),
                'search_keyword': search_keyword if search_keyword else '',
            }
            
            # 3. Selalu perbarui updatedAt setiap kali produk ini di-scrape ulang
            clean_product['updatedAt'] = current_time

            op = UpdateOne(
                filter={'url': clean_product['url']},
                update={
                    '$set': clean_product,
                    # 4. createdAt HANYA diisi jika produk ini benar-benar baru di DB
                    '$setOnInsert': {'createdAt': current_time},
                },
                upsert=True,
            )
            operations.append(op)

        if skipped_count > 0:
            print(f"[-] Total {skipped_count} produk di-skip karena validasi gagal.")
        
        if not operations:
            print(f"[-] Tidak ada produk valid untuk disimpan ke database.")
            return

        try:
            result = self.products_collection.bulk_write(operations)
            print(
                f"[v] Laporan MongoDB ({source_marketplace}): Baru={result.upserted_count}, Diperbarui={result.modified_count}, Total={result.upserted_count + result.modified_count}"
            )
        except Exception as e:
            print(f"[!] Gagal menyimpan ke database: {e}")

    def close(self) -> None:
        self.client.close()
        print("✓ Koneksi database ditutup.")

db = Database()