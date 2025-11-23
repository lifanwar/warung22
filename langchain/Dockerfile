FROM python:3.11-slim

# Direktori kerja
WORKDIR /app

# Supaya output log langsung muncul
ENV PYTHONUNBUFFERED=1

# Install dependency Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .