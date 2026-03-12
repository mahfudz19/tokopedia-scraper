# Multi-Marketplace E-Commerce Scraper 🕸️📦

Alat ekstraksi data (Web Scraper) otomatis yang tangguh menggunakan **Python Playwright**. Dirancang dengan arsitektur modular untuk mengekstrak data produk (Nama, Harga, Toko, Lokasi, dan URL) dari **Tokopedia** dan **Lazada**, lalu menyimpannya langsung ke **MongoDB** terpusat.

Sangat cocok digunakan sebagai *pipeline* awal untuk riset harga, analisis kompetitor, atau pembuatan *dataset Machine Learning*.

## ✨ Fitur Utama
* **Multi-Marketplace Support:** Mendukung scraping dari Tokopedia (rute `/find` & `/search`) dan Lazada (rute `/tag`).
* **MongoDB Integration (Upsert):** Data langsung diunggah ke MongoDB. Menggunakan mekanisme *Upsert* dan indeks unik berdasarkan URL produk untuk **mencegah data duplikat** dan secara otomatis memperbarui harga jika ada perubahan.
* **Anti-Bot & Stealth Mode:** Terintegrasi dengan `playwright-stealth` dan teknik navigasi cerdas untuk menyamarkan *browser* dari sistem deteksi bot (WAF/CAPTCHA).
* **Dual Output System:** Selain ke MongoDB, setiap proses akan menghasilkan cadangan data mentah berupa **JSON** dan **MHTML** (*snapshot* visual halaman utuh yang bisa dibuka secara *offline*) di folder lokal.
* **Batch Processing:** Mendukung pemrosesan banyak kata kunci sekaligus secara otomatis menggunakan file teks.

## 🚀 Prasyarat Sistem
Pastikan perangkat Anda sudah terpasang:
* **Python 3.10** atau lebih baru.
* Akun dan Cluster **MongoDB** (Bisa menggunakan MongoDB Atlas gratis).
* Git.

## 🛠️ Instalasi & Persiapan

1. **Clone repositori dan siapkan Virtual Environment:**
   ```bash
   git clone https://github.com/mahfudz19/tokopedia-scraper.git
   cd tokopedia-scraper
   python -m venv venv
   
   # Aktifkan virtual environment
   # Mac/Linux:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

2. **Install Dependencies & Browser Playwright:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```
   
3. **Konfigurasi Database (PENTING):**
   Buat sebuah file bernama `.env` di folder utama (sejajar dengan `main.py`). Isi file tersebut dengan Connection String MongoDB Anda:
   ```Cuplikan kode
   MONGODB_URI=mongodb+srv://<username>:<password>@cluster0.../scraper?retryWrites=true&w=majority
   ```

## 💻 Cara Penggunaan (CLI)

Program ini menggunakan Argparse dan berjalan sepenuhnya melalui terminal.

**Opsi Argumen:**

- `-k` atau `--keyword` : Untuk mencari satu produk spesifik.
- `-f` atau `--file` : Untuk membaca daftar produk dari file teks (Batch Mode). Default: `keywords.txt`.
- `-m` atau `--method` : Memilih robot scraper (`find` [Tokopedia], `search` [Tokopedia], atau `lazada`). Default: `find`.

**Contoh Eksekusi:**

1. **Menjalankan Satu Keyword (Metode Default /find):**

   ```bash
   python main.py -k "tenda camping"
   ```

2. **Menjalankan Batch Mode (Membaca file `keywords.txt`):**

   ```bash
   python main.py -f keywords.txt
   ```

3. **Eksperimen dengan Metode /search:**
   ```bash
   python main.py -k "helm full face" -m search
   ```
   
1. Scraping Tokopedia (Satu Keyword):
   ```bash
   python main.py -k "helm full face"
   ```
   
2. Scraping Lazada (Satu Keyword):
   ```bash
   python main.py -k "tempat bekal piknik set" -m lazada
   ```
   
3. Batch Mode / Otomatisasi Banyak Keyword:
   Siapkan file `keywords.txt` (isi dengan kata kunci, satu per baris), lalu jalankan:
   ```bash
   python main.py -f keywords.txt -m lazada
   ```
