# Backend Dockerfile for Intelligence Pipeline
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for various packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libc-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and dependencies
# Manual dependency installation to handle Debian Trixie package naming
RUN apt-get update && apt-get install -y \
    # Playwright browser dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    # Fonts (Debian Trixie uses fonts- prefix instead of ttf-)
    fonts-liberation \
    fonts-noto-color-emoji \
    fonts-unifont \
    # Additional dependencies
    libglib2.0-0 \
    libegl1 \
    libgl1 \
    libgles2 \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright chromium browser
RUN playwright install chromium

# Copy application code
COPY . .

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs

# Expose port
EXPOSE 8000

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
