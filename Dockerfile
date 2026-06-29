# Dockerfile Multi-Platform (Support Mac M1/ARM64 dan Linux/AMD64)
# Build: docker buildx build --platform linux/amd64,linux/arm64 -t tokopedia-scraper .
# Run:   docker run -p 8000:8000 -p 6080:6080 -e MONGODB_URI="..." tokopedia-scraper

FROM python:3.11-slim

# Matikan interaksi terminal agar tidak nyangkut saat instalasi
ENV DEBIAN_FRONTEND=noninteractive

# Deteksi arsitektur dan set Chrome flags yang sesuai
ARG TARGETPLATFORM
ENV TARGETPLATFORM=${TARGETPLATFORM:-linux/amd64}

# Install alat GUI, Layar Virtual, dan Chrome Dependencies
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
    libxss1 \
    libgbm1 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libasound2t64 \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome (multi-platform)
RUN if [ "$TARGETPLATFORM" = "linux/arm64" ]; then \
    # ARM64 (Mac M1, Raspberry Pi, dll) - gunakan Chromium dari repo Debian \
    apt-get update && apt-get install -y chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/chromium /usr/bin/google-chrome; \
    else \
    # AMD64 (Linux, Intel Mac) - gunakan Google Chrome resmi \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*; \
    fi

# Install Playwright browsers (multi-platform)
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN pip install --no-cache-dir playwright==1.58.0 && \
    playwright install chromium
RUN playwright install-deps chromium 2>/dev/null || true

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

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Jalankan entrypoint
CMD ["./entrypoint.sh"]
