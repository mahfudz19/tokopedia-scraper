# 🤖 E-Commerce Scraper Bot (Tokopedia, Lazada, Shopee)

Sebuah bot _web scraping_ berbasis Python untuk mengekstrak data produk (nama, harga, lokasi, URL) dari tiga _marketplace_ besar di Indonesia: **Tokopedia**, **Lazada**, dan **Shopee**.

Bot ini dilengkapi dengan sistem _anti-bot bypass_ dan integrasi langsung ke _database_ MongoDB.

## ✨ Fitur Utama

- **Multi-Marketplace Support**: Bisa digunakan untuk Tokopedia, Lazada, dan Shopee.
- **Anti-Bot Bypass**:
  - **Tokopedia & Lazada**: Menggunakan **Playwright** Asynchronous untuk performa tinggi.
  - **Shopee**: Menggunakan **Selenium + Undetected-Chromedriver** untuk menembus pengamanan ketat Datadome Shopee.
- **Auto-Scroll**: Menggulir halaman secara otomatis untuk memuat produk yang menggunakan metode _lazy-loading_.
- **MongoDB Integration**: Menyimpan data produk langsung ke database MongoDB dengan upsert berdasarkan URL.
- **Batch Processing**: Mendukung pencarian banyak _keyword_ sekaligus melalui file `.txt` dengan resume capability.

## ⚙️ Persyaratan Sistem

- Python 3.10 atau lebih baru.
- Google Chrome Browser (Wajib terinstal di OS untuk mode Shopee).
- MongoDB (Berjalan secara lokal atau _cloud_/Atlas).

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

Shopee memiliki sistem pertahanan _anti-bot_ (Datadome) yang sangat ketat. Skrip ini menggunakan pendekatan **"Persistent Session & Manual Intervention"**:

1. Saat pertama kali dijalankan, bot akan memantau apakah ada pengalihan ( _redirect_) ke halaman CAPTCHA atau Login.
2. Jika terdeteksi, **skrip akan dijeda di terminal**.
3. Anda diharuskan menyelesaikan _puzzle_ CAPTCHA atau melakukan Login secara **manual** langsung di jendela _browser_ Chrome yang terbuka.
4. Setelah Anda berhasil lolos dan masuk ke halaman pencarian dengan aman, **kembali ke terminal dan tekan `ENTER`**.
5. Bot akan melanjutkan tugasnya menarik data dan akan menyimpan "paspor" atau status sesi tersebut di dalam folder lokal (`./shopee_profile_uc`).
6. Untuk eksekusi di hari-hari berikutnya, bot akan berjalan sepenuhnya otomatis karena status _login_/kepercayaan Anda sudah tersimpan!

## 📝 Lisensi

Proyek ini dibuat untuk tujuan pembelajaran dan portofolio Data Engineering. Pastikan untuk selalu mematuhi _Terms of Service_ dari masing-masing situs web.

## 🐳 Menjalankan dengan Docker

Proyek ini sudah dilengkapi Dockerfile multi-platform yang mendukung **Mac M1/M2 (ARM64)** dan **Linux/Intel (AMD64)**. Docker image ini sudah mengandung semua yang dibutuhkan: Python, Chromium/Google Chrome, Playwright, Selenium, noVNC, dan FastAPI.

### 📋 Persyaratan

- Docker Desktop atau Docker Engine sudah terinstall.
- File `.env` sudah dibuat dari `.env.example` dan berisi `MONGODB_URI`.

### 1. Konfigurasi Environment

Salin file `.env.example` menjadi `.env`, lalu isi URI MongoDB Anda:

```bash
cp .env.example .env
```

Isi file `.env`:

```env
MONGODB_URI=mongodb://localhost:27017/
```

### 2. Build Docker Image

```bash
docker build -t tokopedia-scraper .
```

### 3. Jalankan Container

```bash
docker run -d \
  --name scraper \
  -p 8000:8000 \
  -p 6080:6080 \
  --env-file .env \
  tokopedia-scraper
```

Atau dengan langsung menyuntikkan environment variable:

```bash
docker run -d \
  --name scraper \
  -p 8000:8000 \
  -p 6080:6080 \
  -e MONGODB_URI="mongodb://localhost:27017/" \
  tokopedia-scraper
```

### 4. Akses Layanan

| Layanan          | URL                          | Keterangan                                           |
| ---------------- | ---------------------------- | ---------------------------------------------------- |
| API Health Check | http://localhost:8000/       | Cek apakah API berjalan                              |
| API Scrape       | http://localhost:8000/scrape | Endpoint POST untuk scraping                         |
| noVNC            | http://localhost:6080        | Akses browser virtual untuk melihat aktivitas Chrome |

### 5. Contoh Request API

```bash
curl -X POST http://localhost:8000/scrape \
  -H "Content-Type: application/json" \
  -d '{"keyword": "macbook m1 pro", "method": "shopee", "head_limit": 1}'
```

Parameter:

- `keyword`: Kata kunci produk yang ingin dicari.
- `method`: Marketplace target. Pilihan: `tokopedia`, `lazada`, `shopee`.
- `head_limit`: Jika lebih dari 0, browser akan ditampilkan di noVNC.

### 6. Perintah Docker yang Berguna

```bash
# Melihat logs container
docker logs -f scraper

# Menghentikan container
docker stop scraper

# Menghapus container
docker rm scraper

# Build ulang tanpa cache
docker build --no-cache -t tokopedia-scraper .

# Build untuk multi-platform (ARM64 + AMD64)
docker buildx build --platform linux/amd64,linux/arm64 -t tokopedia-scraper .
```

### ⚠️ Catatan Penting

- Image Docker ini berukuran besar (~1.5-2GB) karena mengandung browser dan dependencies GUI.
- Pastikan container memiliki minimal **1GB RAM** agar Chrome/Playwright berjalan stabil.
- Untuk Mac M1/M2, Dockerfile akan otomatis menggunakan **Chromium** dari repository Debian karena Google Chrome resmi tidak tersedia untuk ARM64.
- Untuk Linux/Intel, Dockerfile akan menginstall **Google Chrome Stable** resmi.
