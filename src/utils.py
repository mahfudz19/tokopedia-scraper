import json
import os
from datetime import datetime

def save_to_json(data, keyword, prefix="tokopedia"):
    """
    Fungsi bantuan untuk menyimpan list dictionary ke dalam format JSON.
    """
    if not data:
        print("[!] Tidak ada data untuk disimpan.")
        return None

    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/{prefix}_{keyword}_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    print(f"\n[v] Berhasil menyimpan {len(data)} baris data ke {filename}")
    return filename