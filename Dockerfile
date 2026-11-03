FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# System programs the Python libraries rely on:
# - tesseract-ocr: used by pytesseract (OCR)
# - poppler-utils: used by pdf2image (PDF -> images)
# - build tools / cairo: needed to install xhtml2pdf dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libcairo2-dev \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run the tests. Override the command to process a PDF.
CMD ["pytest", "-v"]