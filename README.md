Pembaruan dokumentasi adalah langkah esensial! Sebuah repositori tanpa `README.md` yang merefleksikan pembaruan terkini akan sangat membingungkan developer lain.

Mengingat hasil ekstraksi dari repositori ini akan digunakan sebagai fondasi _dataset_ untuk pengembangan _Machine Learning_, tim pengolah data di proyek ini membutuhkan 4 informasi krusial:

1. **Format dan Lokasi Output Data:** Tim harus tahu bahwa _scraper_ ini menghasilkan dua file sekaligus di folder `data/` (JSON untuk disuapkan ke algoritma ML, dan MHTML untuk _backup_ visual jika terjadi anomali data).
2. **Perbedaan Metode Scrape:** Tim perlu tahu mengapa ada `/find` (stabil untuk produksi dataset) dan `/search` (eksperimental).
3. **Cara Penggunaan CLI (Command Line):** Karena skrip sudah menggunakan `argparse`, tim harus tahu argumen _flag_ apa saja yang tersedia (`-k`, `-f`, `-m`).
4. **Kelebihan dan Kekurangannya:** Agar tim tahu batasan alat ini, misalnya kerentanan terhadap CAPTCHA atau perubahan elemen DOM oleh Tokopedia.

Berikut adalah draf pembaruan `README.md` yang merangkum semua poin di atas dengan padat, profesional, dan relevan dengan alur kerja pengumpulan data:

````markdown
# Tokopedia Scraper (Playwright & Stealth) 🕷️📦

Alat ekstraksi data (Web Scraper) otomatis menggunakan **Python Playwright**. Dirancang khusus dengan arsitektur modular dan CLI (Command Line Interface) untuk mengumpulkan _dataset_ harga dan informasi produk dari Tokopedia. Sangat cocok digunakan sebagai _pipeline_ awal untuk kebutuhan riset data dan _Machine Learning_.

## 🚀 Kelebihan

- **Anti-CSS Randomization:** Menggunakan evaluasi JavaScript internal pada atribut `data-testid` sehingga kebal terhadap pengacakan nama _class_ CSS dari sisi _front-end_ Tokopedia.
- **Dual Output System:** Setiap halaman yang berhasil diproses akan menghasilkan file **JSON** (dataset bersih siap olah) dan **MHTML** (_snapshot_ visual halaman utuh yang bisa dibuka secara _offline_).
- **Stealth Mode:** Terintegrasi dengan `playwright-stealth` untuk menyamarkan _browser_ dari sistem deteksi bot.
- **Dynamic Scrolling:** Mendeteksi tinggi monitor dan melakukan _infinite scroll_ secara dinamis hingga elemen paginasi ditemukan.

## ⚠️ Kekurangan & Limitasi

- **Kecepatan:** Karena menggunakan metode _browser automation_ dengan jeda waktu (_delay_) yang menyerupai manusia untuk menghindari pemblokiran IP, proses _scraping_ tidak secepat mengakses API langsung.
- **Metode /search Rawan Blokir:** Tokopedia memiliki proteksi CAPTCHA dan _firewall_ (seperti Cloudflare) yang sangat agresif pada rute utama pencarian organik (`/search`).
- **Ketergantungan DOM:** Jika pihak platform mengubah struktur atribut `data-testid` secara masif, fungsi ekstraksi JavaScript perlu disesuaikan kembali.

## 🛠️ Instalasi & Persiapan

1. **Clone repositori dan siapkan Virtual Environment:**
   ```bash
   git clone [https://github.com/USERNAME_GITHUB_KAMU/tokopedia-scraper.git](https://github.com/USERNAME_GITHUB_KAMU/tokopedia-scraper.git)
   cd tokopedia-scraper
   python -m venv venv
   source venv/bin/activate
   ```
````

2. **Install Dependencies & Browser Playwright:**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

## 💻 Cara Penggunaan (CLI)

Program ini menggunakan Argparse dan berjalan sepenuhnya melalui terminal.

**Opsi Argumen:**

- `-k` atau `--keyword` : Untuk mencari satu produk spesifik.
- `-f` atau `--file` : Untuk membaca daftar produk dari file teks (Batch Mode). Default: `keywords.txt`.
- `-m` atau `--method` : Memilih rute scraper (`find` atau `search`). Default: `find`.

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

## 📂 Output Data

Semua hasil ekstraksi akan disimpan di dalam direktori `data/` dengan penamaan otomatis berdasakan _keyword_ dan nomor halaman.

- `tokopedia_[keyword]_page_[no].json` -> Struktur data mentah.
- `tokopedia_[keyword]_page_[no].mhtml` -> Visual _web page single-file_.
