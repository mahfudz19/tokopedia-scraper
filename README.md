# 🤖 E-Commerce Scraper Bot (Tokopedia, Lazada, Shopee)

Sebuah bot *web scraping* berbasis Python untuk mengekstrak data produk (nama, harga, lokasi, URL) dari tiga *marketplace* besar di Indonesia: **Tokopedia**, **Lazada**, dan **Shopee**. 

Bot ini dilengkapi dengan sistem *anti-bot bypass*, penyimpanan lokal (JSON & MHTML), dan integrasi langsung ke *database* MongoDB.

## ✨ Fitur Utama

- **Multi-Marketplace Support**: Bisa digunakan untuk Tokopedia, Lazada, dan Shopee.
- **Anti-Bot Bypass**:
  - **Tokopedia & Lazada**: Menggunakan **Playwright** Asynchronous untuk performa tinggi.
  - **Shopee**: Menggunakan **Selenium + Undetected-Chromedriver** untuk menembus pengamanan ketat Datadome Shopee.
- **Auto-Scroll**: Menggulir halaman secara otomatis untuk memuat produk yang menggunakan metode *lazy-loading*.
- **Multi-Output Storage**:
  - Menyimpan data bersih ke dalam file `JSON`.
  - Mengunggah data langsung ke koleksi `MongoDB`.
  - Merekam salinan halaman web dalam format `MHTML` sebagai *backup* visual.
- **Batch Processing**: Mendukung pencarian banyak *keyword* sekaligus melalui file `.txt`.

## ⚙️ Persyaratan Sistem

- Python 3.10 atau lebih baru.
- Google Chrome Browser (Wajib terinstal di OS untuk mode Shopee).
- MongoDB (Berjalan secara lokal atau *cloud*/Atlas).

## 🚀 Instalasi

1. **Clone repositori ini:**
   ```bash
   git clone [https://github.com/mahfudz19/tokopedia-scraper.git](https://github.com/mahfudz19/tokopedia-scraper.git)
   cd tokopedia-scraper
   ```

2. **Buat dan aktifkan Virtual Environment (Opsional namun disarankan):**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Untuk Mac/Linux
   # venv\Scripts\activate   # Untuk Windows
   ```

3. **Instal Library yang dibutuhkan:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Instal Playwright Chromium Browser (Untuk Tokopedia & Lazada):**
   ```bash
   playwright install chromium
   ```

5. **Konfigurasi Environment:**
   - Salin file `.env.example` menjadi `.env`.
   - Atur URL koneksi MongoDB kamu di dalam file `.env` tersebut.
     ```env
     MONGO_URI=mongodb://localhost:27017/
     ```

## 💻 Cara Penggunaan

Skrip utama `main.py` menggunakan argumen CLI (Command Line Interface).

### Argumen yang Tersedia:
- `-k` atau `--keyword`: Untuk mencari satu kata kunci spesifik.
- `-f` atau `--file`: Untuk mencari banyak kata kunci secara berurutan dari file .txt (Default: `keywords.txt`).
- `-m` atau `--method`: Memilih marketplace target. Pilihan: `tokopedia`, `lazada`, `shopee`. (Default: `shopee`).

### Contoh Perintah:

**1. Mencari 1 Keyword di Shopee (Saran untuk pemula):**
```bash
python main.py -k "macbook m1 pro" -m shopee
```

**2. Mencari 1 Keyword di Tokopedia:**
```bash
python main.py -k "tenda camping" -m tokopedia
```

**3. Mencari 1 Keyword di Lazada:**
```bash
python main.py -k "sepatu running" -m lazada
```

**4. Mencari banyak Keyword secara otomatis (Batch Mode):**
Buat daftar kata kunci di file `keywords.txt` (tiap baris 1 kata kunci), lalu jalankan:
```bash
python main.py -f keywords.txt -m shopee
```

## ⚠️ Catatan Khusus untuk Shopee (Datadome Bypass)

Shopee memiliki sistem pertahanan *anti-bot* (Datadome) yang sangat ketat. Skrip ini menggunakan pendekatan **"Persistent Session & Manual Intervention"**:

1. Saat pertama kali dijalankan, bot akan memantau apakah ada pengalihan ( *redirect*) ke halaman CAPTCHA atau Login.
2. Jika terdeteksi, **skrip akan dijeda di terminal**.
3. Anda diharuskan menyelesaikan *puzzle* CAPTCHA atau melakukan Login secara **manual** langsung di jendela *browser* Chrome yang terbuka.
4. Setelah Anda berhasil lolos dan masuk ke halaman pencarian dengan aman, **kembali ke terminal dan tekan `ENTER`**.
5. Bot akan melanjutkan tugasnya menarik data dan akan menyimpan "paspor" atau status sesi tersebut di dalam folder lokal (`./shopee_profile_uc`).
6. Untuk eksekusi di hari-hari berikutnya, bot akan berjalan sepenuhnya otomatis karena status *login*/kepercayaan Anda sudah tersimpan!

## 📝 Lisensi
Proyek ini dibuat untuk tujuan pembelajaran dan portofolio Data Engineering. Pastikan untuk selalu mematuhi *Terms of Service* dari masing-masing situs web.
