# Gunakan Python ringan
FROM --platform=linux/amd64 python:3.10-slim

# Matikan interaksi terminal agar tidak nyangkut saat instalasi
ENV DEBIAN_FRONTEND=noninteractive

# Install alat GUI, Layar Virtual, dan Jaringan
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Asli (Cara Baru)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Atur variabel layar virtual
ENV DISPLAY=:99
ENV RESOLUTION=1024x1024x24

WORKDIR /app

# Install dependency Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code Anda
COPY . .

# Beri izin eksekusi pada script bash
RUN chmod +x entrypoint.sh

# Buka Port (8000 = API, 6080 = noVNC)
EXPOSE 8000 6080

# Jalankan entrypoint
CMD ["./entrypoint.sh"]