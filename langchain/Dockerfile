FROM python:3.11-slim

# Direktori kerja
WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     libstdc++6 \
#     libssl3 \
#     && rm -rf /var/lib/apt/lists/*

# Supaya output log langsung muncul
ENV PYTHONUNBUFFERED=1

# Install dependency Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .