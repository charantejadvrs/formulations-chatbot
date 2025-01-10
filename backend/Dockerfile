# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variable
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/phonic-chariot-443319-u4-7eae24161258.json

# Install Node.js, npm, Puppeteer, and Mermaid CLI
RUN apt-get update && \
    apt-get install -y nodejs npm chromium libnss3 libatk-bridge2.0-0 libx11-xcb1 libgdk-pixbuf2.0-0 \
    libxss1 libasound2 libxtst6 libnspr4 fonts-liberation libappindicator3-1 libatk1.0-0 \
    libatspi2.0-0 libcurl4 libxcomposite1 libxrandr2 libgbm1 --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*  # Clean up

# Install system dependencies for Tesseract OCR and Pillow
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    poppler-utils \
    libtesseract-dev \
    libleptonica-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Puppeteer
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app and custom script into the container
COPY custom_mmdc.js /app/custom_mmdc.js
COPY . /app

# Expose port 5000 for the Flask app
EXPOSE 5000

# Run Gunicorn to serve the Flask app
CMD ["gunicorn", "-w", "4","-k", "gevent", "-b", "0.0.0.0:5000", "app:app"]