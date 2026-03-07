# Tokopedia Scraper (Playwright) 🕷️📦

Project Python ini dibuat untuk mengekstrak data produk (seperti nama dan harga) dari Tokopedia menggunakan **Playwright**. Project ini dikembangkan dengan arsitektur modular dan mendukung dua metode scraping utama: melalui rute `/find/{keyword}` (lebih stabil dan sesuai ToS) dan rute `/search` (eksperimental).

Sangat cocok digunakan untuk mengumpulkan _dataset_ awal guna keperluan riset data atau _Machine Learning_.

## ✨ Fitur Utama

- **Dual Scraping Method:** Menyediakan opsi _scraping_ melalui halaman pencarian organik maupun halaman direktori/SEO.
- **Apple Silicon Optimized:** Berjalan sangat mulus di arsitektur Mac M1/M2 menggunakan _browser_ Chromium bawaan Playwright.
- **Anti-Bot & Error Handling:** Dilengkapi penanganan otomatis untuk halaman _error_ 404 ("Waduh, tujuanmu nggak ada!") dan menggunakan rotasi _User-Agent_ dasar.
- **Modular Codebase:** Kode dipisah dengan rapi (`main.py` terpisah dari modul fungsional di folder `src/`) sehingga mudah dikembangkan lebih lanjut.

## 🚀 Prasyarat Sistem

Pastikan sistem operasi kamu sudah terpasang:

- Python 3.10 atau lebih baru (Sangat direkomendasikan menggunakan `pyenv`)
- Git

## 🛠️ Instalasi & Persiapan

1. **Clone repositori ini:**
   ```
   git clone [https://github.com/USERNAME_GITHUB_KAMU/tokopedia-scraper.git](https://github.com/USERNAME_GITHUB_KAMU/tokopedia-scraper.git)
   cd tokopedia-scraper
   ```

````

2. **Buat dan aktifkan Virtual Environment:**

```
python -m venv venv
source venv/bin/activate  # Untuk macOS/Linux

```

3. **Install Dependencies:**

```
pip install -r requirements.txt

```

4. **Install Browser Playwright:**
   Untuk memastikan Playwright berjalan dengan baik, unduh _binary_ Chromium:

```
playwright install chromium

```

## 💻 Cara Penggunaan

Setelah instalasi selesai, kamu bisa langsung menjalankan _entry point_ aplikasi melalui terminal:

```
python main.py

```

_(Catatan: Kamu dapat memodifikasi kata kunci pencarian atau memilih metode scraping di dalam file `main.py`)_

## 📂 Struktur Direktori

```text
tokopedia-scraper/
├── data/             # Direktori penyimpanan data hasil scraping (CSV/JSON)
├── src/              # Modul utama aplikasi
│   ├── __init__.py
│   ├── scraper_find.py
│   ├── scraper_search.py
│   └── utils.py
├── main.py           # Entry point untuk menjalankan script
├── requirements.txt  # Daftar library Python yang dibutuhkan
└── .gitignore

```

## ⚠️ Disclaimer Hukum & Etika

Project ini dibuat secara eksklusif untuk **tujuan edukasi, riset, dan portofolio**. Melakukan _web scraping_ terhadap platform e-commerce komersial berpotensi melanggar _Terms of Service_ (ToS) dari platform tersebut.

Penulis tidak bertanggung jawab atas pemblokiran IP, pembekuan akun, atau konsekuensi hukum apa pun yang timbul dari penggunaan _script_ ini. Gunakan alat ini dengan bijak, hormati aturan `robots.txt`, dan pertimbangkan beban _server_ target dengan memberikan jeda waktu (_delay_) antar _request_.

```

---

**Saran Tambahan Sebelum Upload ke GitHub:**
Jangan lupa ubah tulisan `USERNAME_GITHUB_KAMU` di bagian instalasi dengan *username* GitHub aslimu nanti.

Dengan selesainya `README.md` ini, fondasi proyekmu sudah setara dengan standar industri. Apakah kamu mau kita mulai mengisi logika kode untuk file `src/scraper_find.py` terlebih dahulu?

```
````
